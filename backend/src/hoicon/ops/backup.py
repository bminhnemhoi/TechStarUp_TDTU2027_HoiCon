"""Sao lưu và khôi phục có mã hóa (spec 034 FR-004, plan D3):

    uv run --directory backend python -m hoicon.ops.backup backup [--dir <thư mục>]
    uv run --directory backend python -m hoicon.ops.backup restore-check [--file <tệp .dump.enc>]
    uv run --directory backend python -m hoicon.ops.backup rotate [--dry-run]

`backup`: `pg_dump -Fc` chạy TRONG container Postgres (`docker exec`, vì máy dev không có `pg_dump`), đọc stdout theo
luồng và mã hóa từng khối 1 MiB bằng AES-256-GCM với `HOICON_BACKUP_KEY_<kid>` (khác khóa dữ liệu). Bản rõ chỉ nằm trong
bộ nhớ và đường ống: KHÔNG bao giờ chạm đĩa. Kèm manifest JSON (số dòng từng bảng đếm trong CÙNG snapshot với dump,
phiên bản alembic, sha256 của bản mã, kid).

Định dạng `*.dump.enc` (phiên bản 2, spec 037 D5): `HCBK` | phiên bản (1 byte) | kid (1 byte) | salt (16 byte),
rồi các khung `độ dài (4 byte, big-endian) | bản mã + thẻ 16 byte`. Khóa con của TỪNG tệp =
HKDF-SHA256(khóa chính, salt) nên hai tệp không bao giờ dùng chung khóa; nonce = 4 byte 0 + chỉ số khối (8 byte).
AAD = `hoicon:backup:v2:<kid>:<chỉ số khối>:<cờ khối cuối>` ⇒ cắt bớt, đảo, nhân đôi hay sửa bất kỳ khối nào đều bị
phát hiện. Phiên bản 1 (tiền tố nonce 4 byte ngẫu nhiên, dùng thẳng khóa chính) vẫn ĐỌC được để khôi phục bản sao lưu
cũ; không còn ghi.

`restore-check`: giải mã, `pg_restore` vào DB tạm `hoicon_restore_check` (trong container), kiểm `alembic_version`,
số dòng từng bảng khớp manifest, các trigger bất biến còn ở chế độ ALWAYS; đo thời gian; luôn xóa DB tạm.
`rotate`: giữ 7 bản theo ngày + 4 bản theo tuần (giờ Việt Nam), xóa phần còn lại.

Lịch chạy và nơi lưu ngoài máy thuộc 012 (docs/setup/BACKUP.md). Chỉ in tên tệp, kích thước, số khối và số dòng.
"""

import argparse
import hashlib
import json
import logging
import os
import re
import struct
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, BinaryIO

import psycopg
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy.engine import make_url

from hoicon.config import Settings, get_settings

MAGIC = b"HCBK"
VERSION = 2
LEGACY_VERSION = 1
SALT_LEN = 16
BLOCK = 1024 * 1024
TAG = 16
HEADER_LEN = len(MAGIC) + 2 + SALT_LEN  # tiêu đề của phiên bản hiện hành (v2)
LEGACY_PREFIX_LEN = 4
TEMP_DB = "hoicon_restore_check"
NAME = re.compile(r"^hoicon-(\d{8}T\d{6}Z)\.dump\.enc$")
VN_TZ = timezone(timedelta(hours=7))  # Việt Nam không có giờ mùa hè
KEEP_DAILY = 7
KEEP_WEEKLY = 4
# Trigger bất biến phải còn nguyên (và ở chế độ ALWAYS = 'A') sau khi khôi phục: bằng chứng đồng ý + nhật ký chuyển.
REQUIRED_TRIGGERS = {
    "trg_consents_immutable": "consents",
    "trg_consents_no_truncate": "consents",
    "trg_incidents_terminal": "incidents",
    "trg_incident_transitions_immutable": "incident_transitions",
}

logger = logging.getLogger(__name__)


class BackupError(Exception):
    """Lỗi sao lưu/khôi phục. Thông điệp không bao giờ chứa khóa hay nội dung dữ liệu."""


# --- mã hóa theo khối ---------------------------------------------------------------------------------------------


def _aad(kid: int, index: int, final: bool, version: int = VERSION) -> bytes:
    return f"hoicon:backup:v{version}:{kid}:{index}:{int(final)}".encode()


def _subkey(key: bytes, salt: bytes) -> bytes:
    """Khóa con của một tệp (v2): HKDF-SHA256(khóa chính, salt riêng của tệp)."""
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=b"hoicon:backup:v2:subkey").derive(key)


def _nonce(prefix: bytes, index: int) -> bytes:
    return prefix + index.to_bytes(8, "big")


def key_for(kid: int, settings: Settings | None = None) -> bytes:
    settings = settings or get_settings()
    value = getattr(settings, f"backup_key_{kid}", None)
    hex_key = value.get_secret_value() if value is not None else ""
    if not re.fullmatch(r"[0-9a-f]{64}", hex_key):
        raise BackupError(f"thiếu hoặc sai định dạng HOICON_BACKUP_KEY_{kid} (hex 64 ký tự)")
    return bytes.fromhex(hex_key)


@dataclass(frozen=True)
class Encrypted:
    blocks: int
    plain_bytes: int
    sha256: str
    size: int


def encrypt_stream(chunks: Iterator[bytes], key: bytes, kid: int, out: BinaryIO) -> Encrypted:
    """Mã hóa luồng `chunks` (mỗi phần ≤ BLOCK) ra `out`. Đọc trước một khối để biết khối nào là khối cuối."""
    salt = os.urandom(SALT_LEN)
    prefix = b"\x00" * 4  # khóa con khác nhau theo tệp nên nonce chỉ cần duy nhất trong tệp (chỉ số khối)
    aead = AESGCM(_subkey(key, salt))
    digest = hashlib.sha256()
    size = 0

    def emit(data: bytes) -> None:
        nonlocal size
        out.write(data)
        digest.update(data)
        size += len(data)

    emit(MAGIC + bytes([VERSION, kid]) + salt)
    index = plain = 0
    pending: bytes | None = None
    for chunk in chunks:
        if pending is not None:
            sealed = aead.encrypt(_nonce(prefix, index), pending, _aad(kid, index, False))
            emit(struct.pack(">I", len(sealed)) + sealed)
            plain += len(pending)
            index += 1
        pending = chunk
    sealed = aead.encrypt(_nonce(prefix, index), pending or b"", _aad(kid, index, True))
    emit(struct.pack(">I", len(sealed)) + sealed)
    plain += len(pending or b"")
    return Encrypted(blocks=index + 1, plain_bytes=plain, sha256=digest.hexdigest(), size=size)


def _read_exact(src: BinaryIO, n: int) -> bytes:
    data = src.read(n)
    if len(data) != n:
        raise BackupError("tệp sao lưu bị cắt cụt")
    return data


def decrypt_stream(src: BinaryIO, settings: Settings | None = None) -> Iterator[bytes]:
    """Giải mã từng khối; sai khóa, sửa 1 byte, cắt cụt, đảo hay chèn khối đều ném `BackupError`."""
    head = _read_exact(src, len(MAGIC) + 2)
    if head[:4] != MAGIC or head[4] not in (VERSION, LEGACY_VERSION):
        raise BackupError("không phải tệp sao lưu HỏiCon (hoặc phiên bản lạ)")
    version, kid = head[4], head[5]
    key = key_for(kid, settings)
    if version == VERSION:
        salt = _read_exact(src, SALT_LEN)
        aead, prefix = AESGCM(_subkey(key, salt)), b"\x00" * 4
    else:  # phiên bản 1: dùng thẳng khóa chính, tiền tố nonce nằm trong tiêu đề
        aead, prefix = AESGCM(key), _read_exact(src, LEGACY_PREFIX_LEN)
    frame = _next_frame(src)
    index = 0
    while frame is not None:
        following = _next_frame(src)
        try:
            yield aead.decrypt(_nonce(prefix, index), frame, _aad(kid, index, following is None, version))
        except InvalidTag:
            raise BackupError("giải mã thất bại: sai khóa, tệp bị sửa, cắt bớt hoặc đảo khối") from None
        frame, index = following, index + 1
    if index == 0:
        raise BackupError("tệp sao lưu không có khối nào")


def _next_frame(src: BinaryIO) -> bytes | None:
    head = src.read(4)
    if head == b"":
        return None
    if len(head) != 4:
        raise BackupError("tệp sao lưu bị cắt cụt")
    (length,) = struct.unpack(">I", head)
    if not TAG <= length <= BLOCK + TAG:
        raise BackupError("khung dữ liệu không hợp lệ")
    return _read_exact(src, length)


# --- Docker / Postgres ---------------------------------------------------------------------------------------------


def _target(settings: Settings) -> tuple[str, str, Any]:
    url = make_url(settings.database_url.get_secret_value())
    if not url.username or not url.database:
        raise BackupError("HOICON_DATABASE_URL thiếu người dùng hoặc tên CSDL")
    return url.username, url.database, url


def _docker(
    settings: Settings, *args: str, stdin: Any = None, stdout: Any = None, stderr: Any = None
) -> subprocess.Popen:
    try:
        return subprocess.Popen(  # noqa: S603 - lệnh cố định; tên container lấy từ cấu hình, không từ đầu vào ngoài
            ["docker", "exec", *(["-i"] if stdin is not None else []), settings.backup_container, *args],  # noqa: S607
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )
    except FileNotFoundError:
        raise BackupError("không có lệnh docker trên máy này") from None


def docker_ready(settings: Settings | None = None) -> bool:
    """Có docker và container Postgres đang chạy không (test dùng để bỏ qua)."""
    settings = settings or get_settings()
    try:
        done = subprocess.run(  # noqa: S603
            ["docker", "inspect", "-f", "{{.State.Running}}", settings.backup_container],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0 and done.stdout.strip() == "true"


def _psql(settings: Settings, database: str, sql: str) -> None:
    user, _, _ = _target(settings)
    with tempfile.TemporaryFile() as err:
        proc = _docker(
            settings, "psql", "-U", user, "-d", database, "-v", "ON_ERROR_STOP=1", "-qAt", "-c", sql, stderr=err
        )
        code = proc.wait()
        if code != 0:
            raise BackupError(f"psql thất bại (mã thoát {code})")  # không in stderr: có thể kèm nội dung hàng dữ liệu


def _conninfo(settings: Settings, database: str | None = None) -> str:
    _, name, url = _target(settings)
    return url.set(drivername="postgresql", database=database or name).render_as_string(hide_password=False)


def _table_counts(cur: psycopg.Cursor) -> dict[str, int]:
    cur.execute(
        "select table_name from information_schema.tables where table_schema = 'public' and table_type = 'BASE TABLE'"
        " order by 1"
    )
    names = [row[0] for row in cur.fetchall()]
    counts: dict[str, int] = {}
    for name in names:
        cur.execute(f'select count(*) from "{name}"')  # noqa: S608 - tên bảng đọc từ information_schema
        counts[name] = cur.fetchone()[0]  # type: ignore[index]
    return counts


def _alembic_version(cur: psycopg.Cursor) -> str:
    cur.execute("select version_num from alembic_version")
    row = cur.fetchone()
    return row[0] if row else ""


def alembic_head() -> str:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[3] / "migrations"))
    return ScriptDirectory.from_config(config).get_current_head() or ""


# --- backup --------------------------------------------------------------------------------------------------------


def backup_dir(settings: Settings, override: Path | None = None) -> Path:
    path = override or (Path(settings.backup_dir) if settings.backup_dir else Path.home() / "hoicon-backups")
    created = not path.exists()
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        if created:
            path.chmod(0o700)
        elif path.stat().st_mode & 0o077:  # thư mục có sẵn (có thể dùng chung): không đổi quyền, chỉ cảnh báo
            logger.warning("backup: thư mục %s cho phép người khác truy cập; nên chmod 700", path)
    return path


def _chunks(stream: BinaryIO) -> Iterator[bytes]:
    while chunk := stream.read(BLOCK):
        yield chunk


@dataclass(frozen=True)
class BackupResult:
    path: Path
    manifest_path: Path
    manifest: dict[str, Any]


def run_backup(
    settings: Settings | None = None, directory: Path | None = None, *, now: datetime | None = None
) -> BackupResult:
    settings = settings or get_settings()
    moment = now or datetime.now(UTC)
    kid = settings.backup_key_kid
    key = key_for(kid, settings)
    user, database, _ = _target(settings)
    target_dir = backup_dir(settings, directory)
    stamp = moment.strftime("%Y%m%dT%H%M%SZ")
    final = target_dir / f"hoicon-{stamp}.dump.enc"
    part = final.with_name(final.name + ".part")
    # Snapshot xuất khẩu: đếm dòng và pg_dump nhìn CÙNG một trạng thái dữ liệu.
    with psycopg.connect(_conninfo(settings)) as conn:
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        with conn.cursor() as cur:
            cur.execute("select pg_export_snapshot()")
            snapshot = cur.fetchone()[0]  # type: ignore[index]
            tables = _table_counts(cur)
            version = _alembic_version(cur)
            with tempfile.TemporaryFile() as err:
                proc = _docker(
                    settings,
                    "pg_dump",
                    "-Fc",
                    "-U",
                    user,
                    f"--snapshot={snapshot}",
                    database,
                    stdout=subprocess.PIPE,
                    stderr=err,
                )
                try:
                    with part.open("wb") as out:
                        if os.name == "posix":
                            os.fchmod(out.fileno(), 0o600)
                        assert proc.stdout is not None  # noqa: S101 - Popen(stdout=PIPE)
                        result = encrypt_stream(_chunks(proc.stdout), key, kid, out)
                    code = proc.wait()
                    if code != 0:
                        raise BackupError(f"pg_dump thất bại (mã thoát {code})")  # không in stderr (có thể kèm dữ liệu)
                except BaseException:
                    proc.kill()
                    part.unlink(missing_ok=True)
                    raise
    part.replace(final)
    manifest = {
        "format": "hoicon-backup/v1",
        "created_at": moment.isoformat(),
        "file": final.name,
        "kid": kid,
        "alembic_version": version,
        "tables": tables,
        "sha256": result.sha256,
        "size": result.size,
        "plaintext_bytes": result.plain_bytes,
        "blocks": result.blocks,
    }
    manifest_path = final.with_name(final.name + ".manifest.json")
    tmp = manifest_path.with_name(manifest_path.name + ".part")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(manifest_path)
    return BackupResult(final, manifest_path, manifest)


# --- restore-check -------------------------------------------------------------------------------------------------


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(BLOCK):
            digest.update(chunk)
    return digest.hexdigest()


def run_restore_check(path: Path, settings: Settings | None = None) -> dict[str, Any]:
    """Khôi phục `path` vào DB tạm và kiểm theo SC-003. Mọi lỗi ⇒ `BackupError`. DB tạm luôn bị xóa."""
    settings = settings or get_settings()
    manifest_path = path.with_name(path.name + ".manifest.json")
    if not manifest_path.exists():
        raise BackupError("thiếu manifest cạnh tệp sao lưu")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sha256_of(path) != manifest["sha256"]:
        raise BackupError("sha256 của tệp không khớp manifest (tệp bị sửa hoặc hỏng)")
    user, _, _ = _target(settings)
    started = time.perf_counter()
    _psql(settings, "postgres", f"DROP DATABASE IF EXISTS {TEMP_DB} WITH (FORCE)")
    _psql(settings, "postgres", f"CREATE DATABASE {TEMP_DB}")
    try:
        with tempfile.TemporaryFile() as err:
            proc = _docker(
                settings,
                "pg_restore",
                "-U",
                user,
                "-d",
                TEMP_DB,
                "--no-owner",
                "--exit-on-error",
                stdin=subprocess.PIPE,
                stderr=err,
            )
            try:
                assert proc.stdin is not None  # noqa: S101 - Popen(stdin=PIPE)
                with path.open("rb") as src:
                    for plain in decrypt_stream(src, settings):
                        proc.stdin.write(plain)
                proc.stdin.close()
                code = proc.wait()
            except BaseException:
                proc.kill()
                raise
            if code != 0:
                raise BackupError(f"pg_restore thất bại (mã thoát {code})")  # không in stderr (kèm nội dung hàng)
        restore_s = time.perf_counter() - started
        with psycopg.connect(_conninfo(settings, TEMP_DB)) as conn, conn.cursor() as cur:
            restored = _table_counts(cur)
            version = _alembic_version(cur)
            cur.execute(
                "select t.tgname, c.relname, t.tgenabled from pg_trigger t join pg_class c on c.oid = t.tgrelid "
                "where not t.tgisinternal"
            )
            triggers = {name: (table, mode) for name, table, mode in cur.fetchall()}
    finally:
        _psql(settings, "postgres", f"DROP DATABASE IF EXISTS {TEMP_DB} WITH (FORCE)")
    problems = []
    if version != manifest["alembic_version"]:
        problems.append("alembic_version khác manifest")
    head = alembic_head()
    if version != head:
        problems.append(f"alembic_version {version} không phải head {head}")
    wrong = sorted(t for t, n in manifest["tables"].items() if restored.get(t) != n)
    if wrong:
        problems.append("số dòng không khớp manifest ở: " + ", ".join(wrong))
    for name, table in REQUIRED_TRIGGERS.items():
        if triggers.get(name) != (table, "A"):
            problems.append(f"trigger {name} thiếu hoặc không ở chế độ ALWAYS")
    report = {
        "file": path.name,
        "ok": not problems,
        "problems": problems,
        "alembic_version": version,
        "tables": len(restored),
        "rows": sum(restored.values()),
        "triggers_always": sorted(n for n, (_, mode) in triggers.items() if mode == "A" and n in REQUIRED_TRIGGERS),
        "restore_seconds": round(restore_s, 2),
        "total_seconds": round(time.perf_counter() - started, 2),
        "temp_database_dropped": True,
    }
    if problems:
        raise BackupError("; ".join(problems))
    return report


# --- rotate --------------------------------------------------------------------------------------------------------


def _stamp(name: str) -> datetime | None:
    match = NAME.match(name)
    return datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC) if match else None


def plan_rotation(names: list[str]) -> tuple[list[str], list[str]]:
    """⇒ (giữ, xóa). Giữ bản MỚI NHẤT của mỗi ngày trong 7 ngày gần nhất có bản, cộng bản mới nhất của mỗi tuần ISO
    trong 4 tuần gần nhất có bản (ngày/tuần tính theo giờ Việt Nam). Tên lạ không bao giờ bị xóa."""
    dated = sorted(((s, n) for n in names if (s := _stamp(n)) is not None), reverse=True)
    keep: set[str] = set()
    days: dict[Any, str] = {}
    weeks: dict[Any, str] = {}
    for stamp, name in dated:  # từ mới tới cũ ⇒ phần tử đầu của mỗi nhóm là bản mới nhất
        local = stamp.astimezone(VN_TZ)
        days.setdefault(local.date(), name)
        weeks.setdefault(local.isocalendar()[:2], name)
    keep.update(list(days.values())[:KEEP_DAILY])
    keep.update(list(weeks.values())[:KEEP_WEEKLY])
    removable = [n for _, n in dated if n not in keep]
    return sorted(keep), sorted(removable)


def run_rotate(directory: Path, *, dry_run: bool = False) -> tuple[list[str], list[str]]:
    names = [p.name for p in directory.iterdir() if NAME.match(p.name)]
    keep, remove = plan_rotation(names)
    if not dry_run:
        for name in remove:
            (directory / name).unlink(missing_ok=True)
            (directory / (name + ".manifest.json")).unlink(missing_ok=True)
    return keep, remove


def newest(directory: Path) -> Path:
    found = sorted((p for p in directory.iterdir() if NAME.match(p.name)), key=lambda p: p.name)
    if not found:
        raise BackupError("chưa có bản sao lưu nào")
    return found[-1]


# --- CLI -----------------------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("backup", help="sao lưu mã hóa")
    make.add_argument("--dir", type=Path, help="thư mục lưu (mặc định HOICON_BACKUP_DIR hoặc ~/hoicon-backups)")
    check = sub.add_parser("restore-check", help="khôi phục vào DB tạm và kiểm")
    check.add_argument("--file", type=Path, help="mặc định: bản mới nhất")
    check.add_argument("--dir", type=Path)
    rotate = sub.add_parser("rotate", help="giữ 7 bản ngày + 4 bản tuần")
    rotate.add_argument("--dir", type=Path)
    rotate.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    try:
        if args.command == "backup":
            result = run_backup(settings, args.dir)
            m = result.manifest
            print(f"Đã sao lưu: {result.path.name} · {m['size']} byte · {m['blocks']} khối · {len(m['tables'])} bảng")
            print(f"Manifest: {result.manifest_path.name} · alembic {m['alembic_version']} · kid {m['kid']}")
        elif args.command == "restore-check":
            path = args.file or newest(backup_dir(settings, args.dir))
            report = run_restore_check(path, settings)
            print(
                f"Khôi phục ĐẠT: {report['file']} · alembic {report['alembic_version']} · {report['tables']} bảng, "
                f"{report['rows']} dòng khớp manifest · trigger ALWAYS: {', '.join(report['triggers_always'])}"
            )
            print(
                f"Thời gian: khôi phục {report['restore_seconds']} s, tổng {report['total_seconds']} s · DB tạm đã xóa"
            )
        else:
            keep, remove = run_rotate(backup_dir(settings, args.dir), dry_run=args.dry_run)
            print(f"Giữ {len(keep)} bản; {'sẽ xóa' if args.dry_run else 'đã xóa'} {len(remove)} bản")
    except BackupError as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
