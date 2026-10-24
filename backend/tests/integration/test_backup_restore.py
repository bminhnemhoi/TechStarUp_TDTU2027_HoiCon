"""Spec 034 FR-004 / SC-003: sao lưu mã hóa AES-256-GCM theo khối + khôi phục kiểm chứng.

Phần mã hóa (khối, AAD, giả mạo) chạy không cần Docker. Phần `pg_dump`/`pg_restore` cần container Postgres dev
(`hoicon-db`) đang chạy; thiếu thì bỏ qua (SKIPPED), không bao giờ coi là đạt."""

import io
import json
import os
import secrets
import struct
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import pytest

from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.ops import backup as bk

pytestmark = pytest.mark.integration

KID = 1
KEY_HEX = "5a" * 32
OTHER_HEX = "a5" * 32


@pytest.fixture(autouse=True)
def backup_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("HOICON_BACKUP_KEY_KID", "1")
    monkeypatch.setenv("HOICON_BACKUP_KEY_1", KEY_HEX)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def seal(chunks: list[bytes], key_hex: str = KEY_HEX, kid: int = KID) -> bytes:
    out = io.BytesIO()
    bk.encrypt_stream(iter(chunks), bytes.fromhex(key_hex), kid, out)
    return out.getvalue()


def open_(data: bytes) -> bytes:
    return b"".join(bk.decrypt_stream(io.BytesIO(data)))


def frames(data: bytes) -> tuple[bytes, list[bytes]]:
    """(tiêu đề, danh sách khung `độ dài + bản mã`) của một tệp đã mã hóa."""
    header, rest, out = data[: bk.HEADER_LEN], data[bk.HEADER_LEN :], []
    while rest:
        (length,) = struct.unpack(">I", rest[:4])
        out.append(rest[: 4 + length])
        rest = rest[4 + length :]
    return header, out


CHUNKS = [b"khoi-mot-" * 100, b"khoi-hai-" * 100, b"khoi-ba-" * 100]


# --- mã hóa theo khối (không cần Docker) -----------------------------------------------------------------------------


def test_round_trip_across_several_blocks() -> None:
    assert open_(seal(CHUNKS)) == b"".join(CHUNKS)


def test_round_trip_of_an_empty_and_a_single_block_dump() -> None:
    assert open_(seal([])) == b""
    assert open_(seal([b"mot khoi"])) == b"mot khoi"


def test_the_ciphertext_hides_the_plaintext_and_differs_each_time() -> None:
    first, second = seal(CHUNKS), seal(CHUNKS)
    assert b"khoi-mot" not in first and first != second  # tiền tố nonce ngẫu nhiên mỗi lần


def test_blocks_are_at_most_1_mib_plus_the_tag() -> None:
    assert bk.BLOCK == 1024 * 1024
    big = os.urandom(bk.BLOCK)
    _, framed = frames(seal([big, big, b"x"]))
    assert [len(f) - 4 for f in framed] == [bk.BLOCK + 16, bk.BLOCK + 16, 1 + 16]


@pytest.mark.parametrize("where", ["header-kid", "first-block", "middle-block", "last-block", "tag"])
def test_flipping_one_byte_anywhere_fails_to_decrypt(where: str) -> None:
    data = bytearray(seal(CHUNKS))
    _, framed = frames(bytes(data))
    offsets = {
        "header-kid": 5,
        "first-block": bk.HEADER_LEN + 4 + 3,
        "middle-block": bk.HEADER_LEN + len(framed[0]) + 4 + 3,
        "last-block": bk.HEADER_LEN + len(framed[0]) + len(framed[1]) + 4 + 3,
        "tag": len(data) - 1,
    }
    data[offsets[where]] ^= 0x01
    with pytest.raises(bk.BackupError):
        open_(bytes(data))


def test_cutting_off_the_last_block_is_detected() -> None:
    header, framed = frames(seal(CHUNKS))
    with pytest.raises(bk.BackupError):
        open_(header + b"".join(framed[:-1]))


def test_cutting_the_file_in_the_middle_of_a_block_is_detected() -> None:
    data = seal(CHUNKS)
    with pytest.raises(bk.BackupError):
        open_(data[:-7])


def test_reordering_two_blocks_is_detected() -> None:
    header, framed = frames(seal(CHUNKS))
    with pytest.raises(bk.BackupError):
        open_(header + framed[1] + framed[0] + framed[2])


def test_duplicating_a_block_is_detected() -> None:
    header, framed = frames(seal(CHUNKS))
    with pytest.raises(bk.BackupError):
        open_(header + framed[0] + framed[1] + framed[1] + framed[2])


def test_appending_bytes_after_the_final_block_is_detected() -> None:
    with pytest.raises(bk.BackupError):
        open_(seal(CHUNKS) + b"\x00\x00\x00\x20" + os.urandom(32))
    with pytest.raises(bk.BackupError):
        open_(seal(CHUNKS) + b"\x01")


def test_a_wrong_key_fails_and_the_error_never_shows_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    data = seal(CHUNKS)
    monkeypatch.setenv("HOICON_BACKUP_KEY_1", OTHER_HEX)
    get_settings.cache_clear()
    with pytest.raises(bk.BackupError) as caught:
        open_(data)
    assert KEY_HEX not in str(caught.value) and OTHER_HEX not in str(caught.value)


def test_a_file_that_is_not_a_backup_is_refused() -> None:
    for junk in (b"", b"PK\x03\x04" + os.urandom(40), b"HCBK\x09\x01" + os.urandom(40)):
        with pytest.raises(bk.BackupError):
            open_(junk)


def test_a_missing_or_malformed_key_is_reported_by_name_only(monkeypatch: pytest.MonkeyPatch) -> None:
    for bad in ("", "zz" * 32, "ab" * 31):
        monkeypatch.setenv("HOICON_BACKUP_KEY_1", bad)
        get_settings.cache_clear()
        with pytest.raises(bk.BackupError) as caught:
            bk.key_for(1)
        assert "HOICON_BACKUP_KEY_1" in str(caught.value) and (bad not in str(caught.value) or bad == "")


def test_an_old_kid_still_decrypts_after_rotating_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    old = seal(CHUNKS)  # kid 1
    monkeypatch.setenv("HOICON_BACKUP_KEY_2", OTHER_HEX)
    monkeypatch.setenv("HOICON_BACKUP_KEY_KID", "2")
    get_settings.cache_clear()
    new = seal(CHUNKS, OTHER_HEX, 2)
    assert open_(old) == open_(new) == b"".join(CHUNKS)
    assert old[5] == 1 and new[5] == 2  # kid nằm trong tiêu đề


# --- xoay vòng 7 ngày + 4 tuần ---------------------------------------------------------------------------------------


def name(moment: datetime) -> str:
    return f"hoicon-{moment.strftime('%Y%m%dT%H%M%SZ')}.dump.enc"


def test_rotation_keeps_seven_days_plus_four_weeks_and_nothing_else() -> None:
    start = datetime(2027, 1, 1, 20, 0, tzinfo=UTC)  # 03:00 giờ VN sáng 02/01
    names = [name(start + timedelta(days=d)) for d in range(60)]  # mỗi ngày một bản, 60 ngày
    keep, remove = bk.plan_rotation(names)
    assert set(keep) | set(remove) == set(names) and not set(keep) & set(remove)
    newest = sorted(names)[-7:]
    assert set(newest) <= set(keep)  # 7 bản ngày gần nhất
    assert 7 <= len(keep) <= 7 + 4
    weekly_extras = set(keep) - set(newest)
    assert len(weekly_extras) <= 4
    assert remove and all(r < min(newest) for r in remove)  # chỉ xóa bản cũ


def test_rotation_keeps_only_the_newest_backup_of_each_day() -> None:
    day = datetime(2027, 3, 1, 1, 0, tzinfo=UTC)
    names = [name(day), name(day + timedelta(hours=3)), name(day + timedelta(hours=6))]
    keep, remove = bk.plan_rotation(names)
    assert keep == [names[2]] and remove == [names[0], names[1]]


def test_rotation_counts_days_in_vietnam_time() -> None:
    # 16:59Z và 17:00Z cùng ngày UTC nhưng khác ngày giờ Việt Nam ⇒ hai bản đều là "bản mới nhất của ngày mình".
    a = name(datetime(2027, 3, 1, 16, 59, tzinfo=UTC))
    b = name(datetime(2027, 3, 1, 17, 0, tzinfo=UTC))
    keep, remove = bk.plan_rotation([a, b])
    assert keep == sorted([a, b]) and remove == []


def test_rotation_never_removes_files_it_does_not_recognise(tmp_path: Path) -> None:
    (tmp_path / "ghi-chu.txt").write_text("giữ")
    old = tmp_path / name(datetime(2020, 1, 1, tzinfo=UTC))
    old.write_bytes(b"x")
    (tmp_path / (old.name + ".manifest.json")).write_text("{}")
    for d in range(40):  # 40 ngày ⇒ bản 2020 cũ hơn 4 tuần gần nhất
        (tmp_path / name(datetime(2027, 3, 1, tzinfo=UTC) + timedelta(days=d))).write_bytes(b"x")
    _, remove = bk.run_rotate(tmp_path, dry_run=True)
    assert old.exists() and old.name in remove  # dry-run không xóa gì
    bk.run_rotate(tmp_path)
    assert not old.exists() and not (tmp_path / (old.name + ".manifest.json")).exists()
    assert (tmp_path / "ghi-chu.txt").exists()


# --- sao lưu thật qua Docker -----------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def docker_or_skip() -> None:
    if not bk.docker_ready():
        pytest.skip("SKIPPED: không có Docker hoặc container Postgres dev (hoicon-db) chưa chạy")


@pytest.fixture(scope="module")
def made(docker_or_skip: None, tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, Any]]:
    """Một bản sao lưu thật của DB dev, kèm một gia đình demo mang chuỗi nhận diện được để tìm trong bản mã."""
    mp = pytest.MonkeyPatch()
    mp.setenv("HOICON_BACKUP_KEY_1", KEY_HEX)
    get_settings.cache_clear()
    settings = get_settings()
    tag = f"BiDanh-Xuyen-{secrets.token_hex(4)}"
    family = new_id()
    with psycopg.connect(bk._conninfo(settings)) as conn:
        conn.execute(
            "insert into families (id, display_name, region, is_demo) values (%s, %s, 'nam', true)", (family, tag)
        )
    directory = tmp_path_factory.mktemp("backups")
    try:
        result = bk.run_backup(settings, directory)
        yield {"result": result, "dir": directory, "tag": tag, "settings": settings}
    finally:
        with psycopg.connect(bk._conninfo(settings)) as conn:
            conn.execute("delete from families where id = %s", (family,))
        mp.undo()
        get_settings.cache_clear()


def test_the_backup_file_holds_no_known_plaintext(made: dict[str, Any]) -> None:
    path: Path = made["result"].path
    blob = path.read_bytes()
    assert made["tag"].encode() not in blob and b"PGDMP" not in blob and b"families" not in blob
    with path.open("rb") as fh:  # nhưng giải mã thì thấy: bản sao lưu thật sự là một dump Postgres
        plain = b"".join(bk.decrypt_stream(fh))
    # dữ liệu bảng trong dump -Fc bị nén nên tìm bí danh thô không có nghĩa; mục lục (tên bảng) thì không nén.
    assert plain.startswith(b"PGDMP") and b"families" in plain and b"consents" in plain


def test_the_backup_leaves_only_the_encrypted_file_and_its_manifest(made: dict[str, Any]) -> None:
    listing = sorted(p.name for p in made["dir"].iterdir())
    assert listing == sorted([made["result"].path.name, made["result"].manifest_path.name])
    assert not any(n.endswith(".part") for n in listing)
    if os.name == "posix":
        assert (made["result"].path.stat().st_mode & 0o777) == 0o600
        assert (made["dir"].stat().st_mode & 0o777) == 0o700


def test_the_manifest_describes_the_backup_and_holds_no_key(made: dict[str, Any]) -> None:
    m = json.loads(made["result"].manifest_path.read_text(encoding="utf-8"))
    assert m["format"] == "hoicon-backup/v1" and m["kid"] == 1 and m["alembic_version"] == bk.alembic_head()
    assert m["sha256"] == bk.sha256_of(made["result"].path) and m["size"] == made["result"].path.stat().st_size
    assert m["tables"]["families"] >= 1 and {"consents", "incidents", "drills", "data_requests"} <= set(m["tables"])
    assert all(isinstance(n, int) and n >= 0 for n in m["tables"].values())
    assert KEY_HEX not in made["result"].manifest_path.read_text(encoding="utf-8")


def test_a_flipped_byte_in_the_real_backup_is_rejected(made: dict[str, Any], tmp_path: Path) -> None:
    data = bytearray(made["result"].path.read_bytes())
    data[len(data) // 2] ^= 0x01
    copy = tmp_path / made["result"].path.name
    copy.write_bytes(bytes(data))
    (tmp_path / (copy.name + ".manifest.json")).write_bytes(made["result"].manifest_path.read_bytes())
    with pytest.raises(bk.BackupError):
        bk.run_restore_check(copy, made["settings"])
    with pytest.raises(bk.BackupError):  # kể cả khi manifest được sửa lại cho khớp sha256: AES-GCM vẫn bắt được
        manifest = json.loads((tmp_path / (copy.name + ".manifest.json")).read_text(encoding="utf-8"))
        manifest["sha256"] = bk.sha256_of(copy)
        (tmp_path / (copy.name + ".manifest.json")).write_text(json.dumps(manifest), encoding="utf-8")
        bk.run_restore_check(copy, made["settings"])
    assert temp_db_exists(made["settings"]) is False


def test_a_truncated_real_backup_is_rejected(made: dict[str, Any], tmp_path: Path) -> None:
    data = made["result"].path.read_bytes()
    _, framed = frames(data)
    assert len(framed) > 1
    cut = tmp_path / made["result"].path.name
    cut.write_bytes(data[: len(data) - len(framed[-1])])
    manifest = json.loads(made["result"].manifest_path.read_text(encoding="utf-8"))
    manifest["sha256"] = bk.sha256_of(cut)
    (tmp_path / (cut.name + ".manifest.json")).write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(bk.BackupError):
        bk.run_restore_check(cut, made["settings"])
    assert temp_db_exists(made["settings"]) is False


def test_a_wrong_key_cannot_restore(made: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOICON_BACKUP_KEY_1", OTHER_HEX)
    get_settings.cache_clear()
    with pytest.raises(bk.BackupError):
        bk.run_restore_check(made["result"].path, get_settings())
    assert temp_db_exists(get_settings()) is False


def temp_db_exists(settings: Any) -> bool:
    with psycopg.connect(bk._conninfo(settings, "postgres")) as conn:
        row = conn.execute("select 1 from pg_database where datname = %s", (bk.TEMP_DB,)).fetchone()
    return row is not None


def test_restore_check_proves_the_backup_restores(made: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    report = bk.run_restore_check(made["result"].path, made["settings"])
    assert report["ok"] is True and report["problems"] == []
    assert report["alembic_version"] == bk.alembic_head()  # SC-003: alembic_version = head
    assert report["rows"] == sum(made["result"].manifest["tables"].values())  # số dòng khớp manifest
    assert set(report["triggers_always"]) == set(bk.REQUIRED_TRIGGERS)  # trigger còn nguyên, chế độ ALWAYS
    assert report["restore_seconds"] > 0 and report["total_seconds"] >= report["restore_seconds"]  # có đo thời gian
    assert temp_db_exists(made["settings"]) is False  # DB tạm đã bị xóa
    print(f"[đo] khôi phục {report['restore_seconds']} s, tổng {report['total_seconds']} s, {report['rows']} dòng")


def test_restore_check_fails_when_the_manifest_row_counts_are_wrong(made: dict[str, Any], tmp_path: Path) -> None:
    copy = tmp_path / made["result"].path.name
    copy.write_bytes(made["result"].path.read_bytes())
    manifest = dict(made["result"].manifest)
    manifest["tables"] = {**manifest["tables"], "families": manifest["tables"]["families"] + 5}
    (tmp_path / (copy.name + ".manifest.json")).write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(bk.BackupError) as caught:
        bk.run_restore_check(copy, made["settings"])
    assert "families" in str(caught.value) and temp_db_exists(made["settings"]) is False


def test_the_cli_runs_backup_restore_and_rotate(
    made: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert bk.main(["backup", "--dir", str(tmp_path)]) == 0
    assert bk.main(["restore-check", "--dir", str(tmp_path)]) == 0
    assert bk.main(["rotate", "--dir", str(tmp_path), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "Đã sao lưu" in out and "Khôi phục ĐẠT" in out and KEY_HEX not in out
    assert made["tag"] not in out  # chỉ in tên tệp, số khối, số dòng


# --- lỗi vận hành ----------------------------------------------------------------------------------------------------


def test_without_a_key_the_cli_fails_cleanly_and_prints_no_secret(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("HOICON_BACKUP_KEY_1", "")
    get_settings.cache_clear()
    assert bk.main(["backup", "--dir", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "HOICON_BACKUP_KEY_1" in err
    assert list(tmp_path.iterdir()) == []  # không để lại tệp dở


def test_a_missing_container_is_reported_and_leaves_no_partial_file(
    docker_or_skip: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOICON_BACKUP_CONTAINER", "khong-co-container-nay")
    get_settings.cache_clear()
    assert bk.docker_ready() is False
    with pytest.raises(bk.BackupError):
        bk.run_backup(get_settings(), tmp_path)
    assert list(tmp_path.iterdir()) == []  # không để lại .part hay bản dở


# --- khôi phục thật vào DB đích: một khối lỗi ⇒ bỏ cả lượt (spec 037 T014, FR-005) -------------------------------

TARGET_DB = "hoicon_restore_atomic_test"


@pytest.fixture
def empty_target(made: dict[str, Any]) -> Iterator[str]:
    settings = made["settings"]
    bk._psql(settings, "postgres", f"DROP DATABASE IF EXISTS {TARGET_DB} WITH (FORCE)")
    bk._psql(settings, "postgres", f"CREATE DATABASE {TARGET_DB}")
    try:
        yield TARGET_DB
    finally:
        bk._psql(settings, "postgres", f"DROP DATABASE IF EXISTS {TARGET_DB} WITH (FORCE)")


def counts_in(settings: Any, database: str) -> dict[str, int]:
    with psycopg.connect(bk._conninfo(settings, database)) as conn, conn.cursor() as cur:
        return bk._table_counts(cur)


def with_manifest(source: Path, data: bytes, directory: Path) -> Path:
    """Chép `data` thành bản sao lưu mới cạnh manifest đã sửa sha256 (để lỗi nằm ở AES-GCM chứ không ở sha)."""
    copy = directory / source.name
    copy.write_bytes(data)
    manifest = json.loads(source.with_name(source.name + ".manifest.json").read_text(encoding="utf-8"))
    manifest["sha256"] = bk.sha256_of(copy)
    (directory / (copy.name + ".manifest.json")).write_text(json.dumps(manifest), encoding="utf-8")
    return copy


def test_restore_atomic_a_good_file_fills_the_empty_target_and_matches_the_manifest(
    made: dict[str, Any], empty_target: str
) -> None:
    report = bk.run_restore(made["result"].path, empty_target, made["settings"])
    assert report["ok"] is True and report["target"] == empty_target
    assert counts_in(made["settings"], empty_target) == made["result"].manifest["tables"]


def test_restore_atomic_a_corrupt_middle_block_leaves_the_target_untouched(
    made: dict[str, Any], empty_target: str, tmp_path: Path
) -> None:
    data = bytearray(made["result"].path.read_bytes())
    _, framed = frames(bytes(data))
    assert len(framed) > 2  # có khối ở giữa để sửa
    offset = bk.HEADER_LEN + sum(4 + len(f) for f in framed[: len(framed) // 2]) + 4 + 8
    data[offset] ^= 0x01  # 1 byte trong khối giữa
    bad = with_manifest(made["result"].path, bytes(data), tmp_path)
    before = counts_in(made["settings"], empty_target)
    with pytest.raises(bk.BackupError):
        bk.run_restore(bad, empty_target, made["settings"])
    assert counts_in(made["settings"], empty_target) == before == {}  # số dòng mọi bảng trước = sau (không có bảng nào)


def test_restore_atomic_refuses_the_live_database_and_a_non_empty_target(
    made: dict[str, Any], empty_target: str
) -> None:
    live = bk._target(made["settings"])[1]
    with pytest.raises(bk.BackupError):
        bk.run_restore(made["result"].path, live, made["settings"])
    bk.run_restore(made["result"].path, empty_target, made["settings"])
    with pytest.raises(bk.BackupError):  # đã có bảng ⇒ không ghi đè
        bk.run_restore(made["result"].path, empty_target, made["settings"])
