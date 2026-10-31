"""Spec 034 FR-003 / SC-002: xóa dữ liệu một gia đình theo yêu cầu. Sau purge không bảng nghiệp vụ nào còn dữ liệu mang
`family_id`/`incident_id`/`member_id`/`thread_id` của gia đình (trừ sổ đồng ý, vết `data_requests`, tombstone ẩn danh),
gia đình đối chứng nguyên vẹn, token cũ ⇒ 401, chạy lại không lỗi.

Danh sách bảng KHÔNG viết cứng: duyệt `information_schema`, nên thêm bảng mới mà quên cập nhật purge ⇒ test này đỏ."""

import secrets
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from consent_support import SHA, call
from sqlalchemy import select, text
from test_incident_graph import deps

from hoicon.agents.runtime import IncidentRuntime, open_checkpointer, prepare_event
from hoicon.agents.spike import demo_event
from hoicon.api.auth import issue_access_token, issue_guardian_access_token
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import (
    ActionToken,
    Consent,
    DataRequest,
    Device,
    Drill,
    Family,
    Incident,
    IncidentTransition,
    Job,
    Member,
    MessageOut,
    PairingCode,
    RiskEventRecord,
    TrustedContact,
    Verification,
)
from hoicon.db.session import get_engine, get_sessionmaker
from hoicon.domain.pii import encrypt_chat_id, hmac_zalo
from hoicon.jobs.queue import run_once
from hoicon.jobs.worker import incident_handlers
from hoicon.services import purge_service

pytestmark = pytest.mark.integration

# Bảng được phép còn dòng của gia đình sau khi xóa: bằng chứng đồng ý, vết yêu cầu, và tombstone đã ẩn danh.
RETAINED = {"consents", "data_requests", "families", "members"}
ELDER_ALIAS = "Bà Tư Hạnh"
GUARDIAN_ALIAS = "Anh Hai Phúc"
BOT = "test-034-bot"


@dataclass
class Built:
    family: UUID
    elder: UUID
    guardian: UUID
    device: UUID
    incident: UUID
    drill: UUID
    zalo_user: str
    runs: list[UUID] = field(default_factory=list)


@pytest.fixture
async def keys(zalo_env: None, service_keys: None) -> None:
    """Pepper, khóa dữ liệu và khóa JWT giả."""


async def build(tag: str) -> Built:
    """Một gia đình đủ dữ liệu: ghép đôi, đồng ý, sự kiện, sự cố, đồ thị đã chạy (có checkpoint), tin Zalo, token,
    xác minh, diễn tập."""
    zalo_user = f"fixture-user-{tag}-{secrets.token_hex(3)}"
    kid, user_hmac = hmac_zalo(BOT, zalo_user)
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=f"Gia đình {tag} {secrets.token_hex(2)}", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        elder = Member(family_id=family.id, role="protected", alias=ELDER_ALIAS[:20], address_form="bác")
        guardian = Member(
            family_id=family.id,
            role="guardian",
            guardian_rank=1,
            alias=GUARDIAN_ALIAS[:20],
            zalo_bot_id=BOT,
            zalo_user_hmac=user_hmac,
            zalo_hmac_kid=kid,
            zalo_chat_enc=encrypt_chat_id(f"chat-{zalo_user}", user_hmac),
        )
        session.add_all([elder, guardian])
        await session.flush()
        device = Device(
            family_id=family.id,
            member_id=elder.id,
            app_version="1",
            rules_version="1",
            device_secret_hash=secrets.token_hex(32),
        )
        session.add(device)
        await session.flush()
        for purpose in ("core_protection", "guardian_alerts", "drills"):
            session.add(
                Consent(
                    family_id=family.id,
                    member_id=elder.id,
                    purpose=purpose,
                    granted=True,
                    consent_version="v1.0",
                    text_sha256=SHA,
                    channel="app",
                )
            )
        session.add(
            TrustedContact(family_id=family.id, member_id=elder.id, phone_hmac="ab" * 32, phone_kid=1, last3="123")
        )
        session.add(
            PairingCode(
                family_id=family.id, code_hash=secrets.token_hex(32), expires_at=datetime.now(UTC) + timedelta(hours=1)
            )
        )
        incident = Incident(
            family_id=family.id,
            member_id=elder.id,
            device_id=device.id,
            level="high",
            rule_floor="high",
            is_demo=True,
        )
        session.add(incident)
        await session.flush()
        session.add(
            IncidentTransition(incident_id=incident.id, from_state="detected", to_state="assessing", actor="system")
        )
        session.add(
            RiskEventRecord(
                id=new_id(),
                family_id=family.id,
                device_id=device.id,
                incident_id=incident.id,
                type="banking_app_foreground",
                rule_floor="high",
                occurred_at=datetime.now(UTC),
                is_drill=False,
                payload={},
            )
        )
        session.add(
            Verification(
                family_id=family.id,
                incident_id=incident.id,
                actor="system",
                kind="phone",
                via="call",
                subject_kid=1,
                subject_hmac="cd" * 32,
                last3="456",
                verdict="unknown",
                confidence=0,
            )
        )
        session.add(
            ActionToken(
                incident_id=incident.id,
                member_id=guardian.id,
                token_hash=secrets.token_hex(32),
                scope="incident_decision",
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        session.add(
            ActionToken(
                member_id=guardian.id,
                token_hash=secrets.token_hex(32),
                scope="guardian_view",
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        now = datetime.now(UTC)
        drill = Drill(
            family_id=family.id,
            member_id=elder.id,
            scheduled_by="ops",
            script_id="drill_bank_card_locked",
            window_start=now - timedelta(hours=2),
            window_end=now - timedelta(hours=1),
            status="declined",
            offered_at=now - timedelta(hours=2),
            is_demo=True,
        )
        session.add(drill)
        await session.flush()
        for template, owner in (("fast_alert", incident.id), ("debrief", drill.id)):
            key = f"{owner}:msg:{template}"
            session.add(
                Job(
                    kind="notify_guardian",
                    payload={"family_id": str(family.id), "template": template, "text": f"nội dung riêng của {tag}"},
                    idempotency_key=key,
                    done_at=now,
                )
            )
            session.add(
                MessageOut(
                    family_id=family.id,
                    incident_id=incident.id if owner == incident.id else None,
                    member_id=guardian.id,
                    channel="zalo",
                    bot_id=BOT,
                    template_id=template,
                    status="sent",
                    quota_month=now.strftime("%Y-%m"),
                    job_key=key,
                )
            )
        ids = Built(family.id, elder.id, guardian.id, device.id, incident.id, drill.id, zalo_user)
    # Đồ thị thật đã chạy: checkpoint + agent_runs/agent_steps + job hẹn giờ/tin của sự cố.
    d = deps()
    async with IncidentRuntime.open(d) as runtime:
        threat, event_data = await prepare_event(d.sessions, demo_event())
        await runtime.start_prepared(
            event_data,
            threat,
            incident_id=str(ids.incident),
            elder_alias="Mẹ",
            is_demo=True,
            family_id=str(ids.family),
        )
    async with get_sessionmaker()() as session:
        ids.runs = list(
            await session.scalars(
                text("select id from agent_runs where thread_id = :t").bindparams(t=str(ids.incident))
            )
        )
    return ids


async def snapshot(ids: Built) -> dict[str, int]:
    """Số dòng thuộc gia đình ở MỌI bảng có cột nhận diện (duyệt information_schema) + các bảng gián tiếp."""
    async with get_engine().connect() as conn:
        tables = (
            await conn.execute(
                text(
                    "select table_name, array_agg(column_name::text) from information_schema.columns "
                    "where table_schema = 'public' "
                    "and column_name in ('family_id', 'incident_id', 'member_id', 'thread_id') "
                    "group by table_name order by 1"
                )
            )
        ).all()
        family_incidents = [str(ids.incident)]
        members = [str(ids.elder), str(ids.guardian)]
        counts: dict[str, int] = {}
        for table, columns in tables:
            clauses, params = [], {}
            if "family_id" in columns:
                clauses.append("family_id = :f")
                params["f"] = ids.family
            if "incident_id" in columns:
                clauses.append("incident_id = ANY(CAST(:i AS uuid[]))")
                params["i"] = family_incidents
            if "member_id" in columns:
                clauses.append("member_id = ANY(CAST(:m AS uuid[]))")
                params["m"] = members
            if "thread_id" in columns:
                clauses.append("thread_id = ANY(:t)")
                params["t"] = family_incidents
            sql = f'select count(*) from "{table}" where ' + " or ".join(clauses)  # noqa: S608 - tên bảng từ information_schema
            counts[table] = (await conn.execute(text(sql), params)).scalar_one()
        counts["jobs"] = (
            await conn.execute(
                text(
                    "select count(*) from jobs where kind <> 'purge_family' and (payload->>'family_id' = :f "
                    "or idempotency_key like any(:keys))"
                ),
                {"f": str(ids.family), "keys": [f"{ids.incident}:%", f"{ids.drill}:%"]},
            )
        ).scalar_one()
        counts["agent_steps"] = (
            await conn.execute(text("select count(*) from agent_steps where run_id = ANY(:r)"), {"r": ids.runs})
        ).scalar_one()
    return counts


@pytest.fixture
async def worlds(require_db: None, keys: None) -> AsyncGenerator[tuple[Built, Built]]:
    target, control = await build("muc-tieu"), await build("doi-chung")
    yield target, control
    for built in (target, control):
        async with get_engine().begin() as conn:
            await conn.execute(text("alter table consents disable trigger trg_consents_immutable"))
            await conn.execute(text("delete from consents where family_id = :f"), {"f": built.family})
            await conn.execute(text("alter table consents enable always trigger trg_consents_immutable"))
            await conn.execute(text("delete from data_requests where family_id = :f"), {"f": built.family})
            await conn.execute(
                text(
                    "delete from jobs where idempotency_key like :a or idempotency_key like :b "
                    "or payload->>'family_id' = :f"
                ),
                {"a": f"{built.incident}:%", "b": f"{built.drill}:%", "f": str(built.family)},
            )
            for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                await conn.execute(text(f"delete from {table} where thread_id = :t"), {"t": str(built.incident)})  # noqa: S608
            await conn.execute(text("delete from agent_runs where thread_id = :t"), {"t": str(built.incident)})
            await conn.execute(text("delete from families where id = :f"), {"f": built.family})


async def purge(built: Built, request_id: UUID | None = None) -> dict[str, int]:
    url = get_settings().database_url.get_secret_value()
    async with open_checkpointer(url) as saver:
        return await purge_service.purge_family(
            get_sessionmaker(), saver.adelete_thread, built.family, request_id=request_id
        )


# --- dữ liệu dựng đủ trước khi xóa (để "0 dòng" sau đó có nghĩa) -------------------------------------------------


async def test_the_fixture_really_holds_data_in_every_kind_of_table(worlds: tuple[Built, Built]) -> None:
    before = await snapshot(worlds[0])
    for table in (
        "devices",
        "drills",
        "incidents",
        "incident_transitions",
        "messages_out",
        "pairing_codes",
        "risk_events",
        "trusted_contacts",
        "verifications",
        "action_tokens",
        "agent_runs",
        "agent_steps",
        "checkpoints",
        "jobs",
        "consents",
        "members",
    ):
        assert before.get(table, 0) > 0, f"dữ liệu dựng thiếu bảng {table}: test xóa sẽ không có nghĩa"


# --- SC-002 ------------------------------------------------------------------------------------------------------


async def test_after_the_purge_no_business_table_holds_the_family(worlds: tuple[Built, Built]) -> None:
    target, _ = worlds
    request = await purge_service.request_delete(get_sessionmaker(), target.family, "ops")
    await purge(target, request.id)
    after = await snapshot(target)
    leftovers = {table: n for table, n in after.items() if n and table not in RETAINED}
    assert leftovers == {}, f"còn dữ liệu của gia đình đã xóa ở: {leftovers}"
    assert after["consents"] == 3 and after["data_requests"] == 1


async def test_the_zalo_quota_counter_survives_but_every_link_to_the_family_is_cut(
    worlds: tuple[Built, Built],
) -> None:
    """Review 034 #10: xóa gia đình không được làm hạn mức 3.000 tin/tháng đếm thiếu; dòng còn, liên kết thì đứt."""
    target, _ = worlds

    async def counted() -> int:
        async with get_sessionmaker()() as session:
            return await session.scalar(text("select count(*) from messages_out where bot_id = :b"), {"b": BOT}) or 0

    before = await counted()
    assert before > 0
    await purge(target)
    assert await counted() == before
    async with get_sessionmaker()() as session:
        linked = await session.scalar(
            text(
                "select count(*) from messages_out where family_id = :f or incident_id = :i or member_id = :m "
                "or job_key like :k"
            ),
            {"f": target.family, "i": target.incident, "m": target.guardian, "k": f"{target.incident}:%"},
        )
    assert linked == 0


async def test_consents_are_kept_exactly_as_they_were(worlds: tuple[Built, Built]) -> None:
    target, _ = worlds

    async def ledger() -> list[tuple[Any, ...]]:
        async with get_sessionmaker()() as session:
            rows = await session.execute(
                select(
                    Consent.id,
                    Consent.member_id,
                    Consent.purpose,
                    Consent.granted,
                    Consent.text_sha256,
                    Consent.recorded_at,
                )
                .where(Consent.family_id == target.family)
                .order_by(Consent.id)
            )
            return [tuple(r) for r in rows]

    before = await ledger()
    await purge(target)
    assert before and await ledger() == before


async def test_families_and_members_become_anonymous_tombstones(worlds: tuple[Built, Built]) -> None:
    target, control = worlds
    await purge(target)
    async with get_sessionmaker()() as session:
        family = await session.get(Family, target.family)
        members = list(await session.scalars(select(Member).where(Member.family_id == target.family)))
        dump = (
            (
                await session.execute(
                    text("select row_to_json(m)::text from members m where family_id = :f"), {"f": target.family}
                )
            )
            .scalars()
            .all()
        )
    assert family is not None and family.display_name == purge_service.TOMBSTONE and family.deleted_at is not None
    assert len(members) == 2
    for member in members:
        assert member.alias == purge_service.TOMBSTONE and member.deleted_at is not None
        assert member.address_form is None
        assert (member.zalo_bot_id, member.zalo_user_hmac, member.zalo_hmac_kid, member.zalo_chat_enc) == (None,) * 4
    joined = " ".join(dump)
    assert target.zalo_user not in joined and "Hạnh" not in joined and "Phúc" not in joined
    async with get_sessionmaker()() as session:  # đối chứng không bị ẩn danh
        other = await session.get(Family, control.family)
        assert other is not None and other.deleted_at is None and other.display_name != purge_service.TOMBSTONE
        other_members = list(await session.scalars(select(Member).where(Member.family_id == control.family)))
    assert all(m.deleted_at is None and m.alias != purge_service.TOMBSTONE for m in other_members)
    assert any(m.zalo_chat_enc for m in other_members)


async def test_the_control_family_is_untouched(worlds: tuple[Built, Built]) -> None:
    target, control = worlds
    before = await snapshot(control)
    await purge(target)
    assert await snapshot(control) == before


async def test_a_leftover_zalo_update_job_carrying_the_guardians_identity_is_deleted(
    worlds: tuple[Built, Built],
) -> None:
    target, control = worlds
    async with get_sessionmaker()() as session:
        mine = await session.scalar(select(Member.zalo_user_hmac).where(Member.id == target.guardian))
        theirs = await session.scalar(select(Member.zalo_user_hmac).where(Member.id == control.guardian))
    async with get_sessionmaker().begin() as session:
        for owner in (mine, theirs):
            session.add(
                Job(kind="zalo_update", payload={"user_hmac": owner, "chat_enc": "x"}, idempotency_key=f"zu-{owner}")
            )
    await purge(target)
    async with get_sessionmaker()() as session:
        left = set(await session.scalars(select(Job.idempotency_key).where(Job.kind == "zalo_update")))
        await session.execute(text("select 1"))
    assert f"zu-{mine}" not in left and f"zu-{theirs}" in left
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from jobs where idempotency_key = :k"), {"k": f"zu-{theirs}"})


async def test_the_text_of_the_messages_is_gone_from_the_jobs_table(worlds: tuple[Built, Built]) -> None:
    target, _ = worlds
    await purge(target)
    async with get_sessionmaker()() as session:
        mine = await session.scalar(text("select count(*) from jobs where payload::text like '%muc-tieu%'"))
        theirs = await session.scalar(text("select count(*) from jobs where payload::text like '%doi-chung%'"))
    assert mine == 0 and theirs and theirs > 0


async def test_old_device_and_guardian_tokens_are_refused_afterwards(worlds: tuple[Built, Built]) -> None:
    target, control = worlds
    device_token = issue_access_token(target.device, target.family, target.elder)
    guardian_token = issue_guardian_access_token(target.guardian, target.family)
    other_device = issue_access_token(control.device, control.family, control.elder)
    other_guardian = issue_guardian_access_token(control.guardian, control.family)
    assert (await call("GET", "/v1/devices/me", token=device_token)).status_code == 200
    assert (await call("GET", "/v1/guardian/me", token=guardian_token)).status_code == 200
    await purge(target)
    assert (await call("GET", "/v1/devices/me", token=device_token)).status_code == 401
    assert (await call("GET", "/v1/guardian/me", token=guardian_token)).status_code == 401
    assert (await call("GET", "/v1/devices/me", token=other_device)).status_code == 200  # gia đình đối chứng sống
    assert (await call("GET", "/v1/guardian/me", token=other_guardian)).status_code == 200


async def test_devices_are_revoked_before_anything_is_deleted(worlds: tuple[Built, Built]) -> None:
    """Thu hồi thiết bị TRƯỚC (bước 1): xóa checkpoint hỏng giữa chừng thì máy vẫn đã bị chặn."""
    target, _ = worlds

    async def boom(_: str) -> None:
        raise RuntimeError("checkpoint store down")

    with pytest.raises(RuntimeError):
        await purge_service.purge_family(get_sessionmaker(), boom, target.family)
    async with get_sessionmaker()() as session:
        device = await session.get(Device, target.device)
        incidents = await session.scalar(
            text("select count(*) from incidents where family_id = :f"), {"f": target.family}
        )
    assert device is not None and device.revoked_at is not None  # đã thu hồi
    assert incidents == 1  # chưa xóa gì sau bước lỗi


async def test_guardian_tokens_are_closed_before_anything_is_deleted(worlds: tuple[Built, Built]) -> None:
    """Đóng cửa trước (bước 1): xóa checkpoint hỏng giữa chừng thì người giám hộ cũng đã bị chặn, không ghi thêm gì."""
    target, _ = worlds
    guardian_token = issue_guardian_access_token(target.guardian, target.family)

    async def boom(_: str) -> None:
        raise RuntimeError("checkpoint store down")

    with pytest.raises(RuntimeError):
        await purge_service.purge_family(get_sessionmaker(), boom, target.family)
    assert (await call("GET", "/v1/guardian/me", token=guardian_token)).status_code == 401
    async with get_sessionmaker()() as session:
        deleted_at = await session.scalar(text("select deleted_at from families where id = :f"), {"f": target.family})
    assert deleted_at is not None


async def test_checkpoints_are_swept_again_once_the_jobs_are_gone(worlds: tuple[Built, Built]) -> None:
    """`graph_resume` chạy dở có thể ghi lại checkpoint sau lần xóa đầu ⇒ quét lần hai khi đã hết job."""
    target, _ = worlds
    seen: list[tuple[str, int]] = []

    async def spy(thread: str) -> None:
        async with get_sessionmaker()() as session:
            jobs = await session.scalar(
                text("select count(*) from jobs where idempotency_key like :k"), {"k": f"{target.incident}:%"}
            )
        seen.append((thread, jobs or 0))

    await purge_service.purge_family(get_sessionmaker(), spy, target.family)
    mine = [jobs for thread, jobs in seen if thread == str(target.incident)]
    assert len(mine) == 2 and mine[0] > 0 and mine[-1] == 0


# --- vòng đời yêu cầu ------------------------------------------------------------------------------------------------


async def test_the_request_goes_pending_then_done_and_a_failure_is_recorded_then_recovered(
    worlds: tuple[Built, Built],
) -> None:
    target, _ = worlds
    request = await purge_service.request_delete(get_sessionmaker(), target.family, "ops")
    assert (request.status, request.kind, request.requested_via, request.completed_at) == (
        "pending",
        "delete",
        "ops",
        None,
    )
    again = await purge_service.request_delete(get_sessionmaker(), target.family, "web")
    assert again.id == request.id  # đang chờ ⇒ không tạo yêu cầu thứ hai
    async with get_sessionmaker()() as session:
        queued = list(await session.scalars(select(Job).where(Job.idempotency_key == f"purge:{request.id}")))
    assert len(queued) == 1 and queued[0].kind == "purge_family"
    assert queued[0].payload == {"request_id": str(request.id), "family_id": str(target.family)}  # chỉ id

    async def boom(_: str) -> None:
        raise ValueError("x")

    with pytest.raises(ValueError):
        await purge_service.purge_family(get_sessionmaker(), boom, target.family, request_id=request.id)
    async with get_sessionmaker()() as session:
        failed = await session.get(DataRequest, request.id)
    assert failed is not None and failed.status == "failed" and failed.error_code == "ValueError"
    assert failed.completed_at is None
    await purge(target, request.id)  # thử lại thành công
    async with get_sessionmaker()() as session:
        done = await session.get(DataRequest, request.id)
    assert done is not None and done.status == "done" and done.error_code is None and done.completed_at is not None


async def test_running_it_twice_is_harmless(worlds: tuple[Built, Built]) -> None:
    target, _ = worlds
    request = await purge_service.request_delete(get_sessionmaker(), target.family, "ops")
    first = await purge(target, request.id)
    second = await purge(target, request.id)
    assert first["incidents"] == 1 and second["incidents"] == 0 and second["devices"] == 0
    after = await snapshot(target)
    assert {t: n for t, n in after.items() if n and t not in RETAINED} == {}


async def test_an_unknown_family_is_refused(require_db: None) -> None:
    with pytest.raises(purge_service.FamilyNotFoundError):
        await purge_service.request_delete(get_sessionmaker(), new_id(), "ops")


async def test_the_worker_runs_the_purge_job(worlds: tuple[Built, Built]) -> None:
    target, control = worlds
    request = await purge_service.request_delete(get_sessionmaker(), target.family, "ops")
    d = deps()
    async with IncidentRuntime.open(d) as runtime:
        for _ in range(40):
            await run_once(d.sessions, incident_handlers(runtime), "test-purge-worker")
            async with get_sessionmaker()() as session:
                row = await session.get(DataRequest, request.id)
            if row is not None and row.status == "done":
                break
    assert row is not None and row.status == "done"
    after = await snapshot(target)
    assert {t: n for t, n in after.items() if n and t not in RETAINED} == {}
    assert (await snapshot(control))["incidents"] == 1


async def test_the_purge_does_not_log_names_or_ids_of_people(
    worlds: tuple[Built, Built], caplog: pytest.LogCaptureFixture
) -> None:
    target, _ = worlds
    with caplog.at_level("DEBUG"):
        await purge(target)
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert ELDER_ALIAS not in logged and GUARDIAN_ALIAS not in logged and target.zalo_user not in logged
    assert str(target.family) not in logged and "Hạnh" not in logged
