"""Spec 034 FR-008: role `hoicon_app` (không sở hữu bảng) bị từ chối sửa sổ đồng ý và nhật ký chuyển bằng QUYỀN, không
chỉ bằng trigger, và không tắt được trigger. Tạo role trên DB dev rồi dọn lại sau test."""

import re
import secrets
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg import errors, sql
from sqlalchemy.engine import make_url

from hoicon.config import get_settings
from hoicon.db.ids import new_id

pytestmark = pytest.mark.integration

ROLES_SQL = Path(__file__).resolve().parents[3] / "infra" / "postgres" / "roles.sql"
SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def owner_conninfo() -> str:
    return (
        make_url(get_settings().database_url.get_secret_value())
        .set(drivername="postgresql")
        .render_as_string(hide_password=False)
    )


def app_conninfo(password: str) -> str:
    url = make_url(get_settings().database_url.get_secret_value())
    return url.set(drivername="postgresql", username="hoicon_app", password=password).render_as_string(
        hide_password=False
    )


@pytest.fixture
def role(require_db: None) -> Iterator[dict[str, Any]]:
    """Áp `roles.sql` bằng role chủ, đặt mật khẩu tạm cho `hoicon_app`, dựng 1 gia đình + 1 thành viên + 1 sự cố.
    Mọi bước dựng nằm trong `try`: lỗi giữa chừng vẫn dọn role và dữ liệu."""
    password = secrets.token_urlsafe(24)
    family, member, incident = new_id(), new_id(), new_id()
    with psycopg.connect(owner_conninfo(), autocommit=True) as owner:
        if owner.execute("select 1 from pg_roles where rolname = 'hoicon_app'").fetchone():
            pytest.skip("role hoicon_app đã có trên DB dev (có thể đang được dùng): không đụng")
        try:
            owner.execute(ROLES_SQL.read_text(encoding="utf-8"))
            owner.execute(sql.SQL("ALTER ROLE hoicon_app PASSWORD {}").format(sql.Literal(password)))
            owner.execute(
                "insert into families (id, display_name, region, is_demo) values (%s, 'test-034-roles', 'nam', true)",
                (family,),
            )
            owner.execute("insert into members (id, family_id, role) values (%s, %s, 'protected')", (member, family))
            owner.execute(
                "insert into incidents (id, family_id, member_id, level, rule_floor) "
                "values (%s, %s, %s, 'high', 'high')",
                (incident, family, member),
            )
            owner.execute(
                "insert into incident_transitions (id, incident_id, from_state, to_state, actor) "
                "values (%s, %s, 'detected', 'assessing', 'system')",
                (new_id(), incident),
            )
            owner.execute(
                "insert into consents (id, family_id, member_id, purpose, granted, consent_version, text_sha256, "
                "channel) values (%s, %s, %s, 'core_protection', true, 'v1.0', %s, 'app')",
                (new_id(), family, member, SHA),
            )
            yield {"password": password, "family": family, "member": member, "incident": incident}
        finally:
            owner.execute("alter table consents disable trigger trg_consents_immutable")
            owner.execute("delete from consents where family_id = %s", (family,))
            owner.execute("alter table consents enable always trigger trg_consents_immutable")
            owner.execute("delete from families where id = %s", (family,))
            owner.execute("drop owned by hoicon_app")
            owner.execute("drop role if exists hoicon_app")


@pytest.fixture
def app(role: dict[str, Any]) -> Iterator[psycopg.Connection]:
    with psycopg.connect(app_conninfo(role["password"]), autocommit=True) as conn:
        yield conn


def denied(conn: psycopg.Connection, statement: str, params: tuple = ()) -> None:
    """Câu lệnh phải bị từ chối bởi QUYỀN (42501), không phải bởi trigger hay lý do khác."""
    with pytest.raises(errors.InsufficientPrivilege):
        conn.execute(statement, params)  # type: ignore[arg-type]


def test_the_role_is_unprivileged_and_owns_nothing(app: psycopg.Connection) -> None:
    row = app.execute(
        "select rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls from pg_roles "
        "where rolname = current_user"
    ).fetchone()
    assert row == (False, False, False, False, False)
    assert app.execute("select count(*) from pg_tables where tableowner = current_user").fetchone() == (0,)
    assert app.execute(
        "select count(*) from pg_class where relowner = (select oid from pg_roles where rolname = current_user)"
    ).fetchone() == (0,)


def test_the_ledger_can_be_read_and_appended_to(app: psycopg.Connection, role: dict[str, Any]) -> None:
    assert app.execute("select count(*) from consents where family_id = %s", (role["family"],)).fetchone() == (1,)
    app.execute(
        "insert into consents (id, family_id, member_id, purpose, granted, consent_version, text_sha256, channel) "
        "values (%s, %s, %s, 'guardian_alerts', false, 'v1.0', %s, 'app')",
        (new_id(), role["family"], role["member"], SHA),
    )
    app.execute(
        "insert into incident_transitions (id, incident_id, from_state, to_state, actor) "
        "values (%s, %s, 'assessing', 'awaiting_guardian', 'system')",
        (new_id(), role["incident"]),
    )
    assert app.execute("select count(*) from consents where family_id = %s", (role["family"],)).fetchone() == (2,)


@pytest.mark.parametrize("table", ["consents", "incident_transitions"])
def test_update_delete_and_truncate_of_the_ledgers_are_refused_by_privilege(
    app: psycopg.Connection, table: str
) -> None:
    column = "granted" if table == "consents" else "actor"
    value = "false" if table == "consents" else "'x'"
    denied(app, f"update {table} set {column} = {value}")  # noqa: S608
    denied(app, f"delete from {table}")  # noqa: S608
    denied(app, f"truncate {table}")


@pytest.mark.parametrize(
    "statement",
    [
        "alter table consents disable trigger trg_consents_immutable",
        "alter table consents disable trigger all",
        "alter table consents disable trigger user",
        "alter table incident_transitions disable trigger trg_incident_transitions_immutable",
        "alter table incidents disable trigger trg_incidents_terminal",
        "drop trigger trg_consents_immutable on consents",
        "drop table consents",
        "alter table consents add column note text",
        "alter table consents rename to consents_old",
        "create table sneaky (id int)",
        "drop function prevent_consent_tamper() cascade",
    ],
)
def test_the_triggers_and_the_schema_cannot_be_touched(app: psycopg.Connection, statement: str) -> None:
    denied(app, statement)


def test_the_trigger_is_still_enabled_and_is_not_the_only_barrier(app: psycopg.Connection) -> None:
    """Đối chứng: các trigger vẫn bật (chế độ ALWAYS); `hoicon_app` bị chặn ở tầng quyền, trước cả trigger."""
    modes = dict(
        app.execute(
            "select tgname, tgenabled from pg_trigger where tgname like 'trg\\_%' and not tgisinternal"
        ).fetchall()
    )
    assert modes["trg_consents_immutable"] == "A" and modes["trg_incident_transitions_immutable"] == "A"


def test_the_application_still_works_on_ordinary_tables(app: psycopg.Connection, role: dict[str, Any]) -> None:
    job = new_id()
    app.execute("insert into jobs (id, kind, payload) values (%s, 'test_roles', '{}'::jsonb)", (job,))
    app.execute("update jobs set attempts = 1 where id = %s", (job,))
    assert app.execute("select attempts from jobs where id = %s", (job,)).fetchone() == (1,)
    app.execute("delete from jobs where id = %s", (job,))
    app.execute("update incidents set level = 'critical' where id = %s", (role["incident"],))
    app.execute("update members set alias = 'Mẹ' where id = %s", (role["member"],))


def test_alembic_version_is_not_readable_by_the_application(app: psycopg.Connection) -> None:
    denied(app, "select * from alembic_version")
    denied(app, "update alembic_version set version_num = '0000'")


def test_cascading_deletes_still_work_without_delete_privilege_on_the_ledger(
    app: psycopg.Connection, role: dict[str, Any]
) -> None:
    """Xóa sự cố kéo theo nhật ký chuyển: hành động tham chiếu chạy với quyền của chủ bảng, trigger cho phép."""
    incident = new_id()
    app.execute(
        "insert into incidents (id, family_id, member_id, level, rule_floor) values (%s, %s, %s, 'high', 'high')",
        (incident, role["family"], role["member"]),
    )
    app.execute(
        "insert into incident_transitions (id, incident_id, from_state, to_state, actor) "
        "values (%s, %s, 'detected', 'assessing', 'system')",
        (new_id(), incident),
    )
    app.execute("delete from incidents where id = %s", (incident,))
    assert app.execute("select count(*) from incident_transitions where incident_id = %s", (incident,)).fetchone() == (
        0,
    )


def test_roles_sql_is_idempotent_and_carries_no_password(role: dict[str, Any]) -> None:
    text = ROLES_SQL.read_text(encoding="utf-8")
    assert not re.search(r"(?i)password\s+'", text) and "PASSWORD" not in text.replace("\\password", "").split("--")[0]
    with psycopg.connect(owner_conninfo(), autocommit=True) as owner:
        owner.execute(text)  # chạy lại lần hai không lỗi
        owner.execute(text)


def test_a_table_added_later_is_covered_when_the_script_is_rerun(role: dict[str, Any]) -> None:
    with psycopg.connect(owner_conninfo(), autocommit=True) as owner:
        owner.execute("create table zz_034_new (id int primary key)")
        try:
            owner.execute(ROLES_SQL.read_text(encoding="utf-8"))
            with psycopg.connect(app_conninfo(role["password"]), autocommit=True) as app:
                app.execute("insert into zz_034_new values (1)")
                app.execute("delete from zz_034_new")
        finally:
            owner.execute("drop table zz_034_new")


def test_a_table_added_by_a_later_migration_is_usable_without_rerunning_the_script(role: dict[str, Any]) -> None:
    """Spec 012 T020 / Medium #8 của 034: `ALTER DEFAULT PRIVILEGES` cấp quyền cho bảng tạo sau, khỏi chạy lại roles.sql."""
    with psycopg.connect(owner_conninfo(), autocommit=True) as owner:
        owner.execute("create table zz_012_later (id int primary key)")
        try:
            with psycopg.connect(app_conninfo(role["password"]), autocommit=True) as app:
                app.execute("insert into zz_012_later values (1)")
                app.execute("delete from zz_012_later")
        finally:
            owner.execute("drop table zz_012_later")
