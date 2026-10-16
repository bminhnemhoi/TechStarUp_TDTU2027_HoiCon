"""Nạp danh sách đe dọa vào Postgres (spec 003, ADR-006): máy chủ CHỈ lưu `HMAC(pepper[kid], h1)` + 3 số cuối.
Spec 026 (ADR-011): mỗi chỉ báo còn có `bucket_enc` = bucket 24 bit của h1 đã MÃ HÓA (khóa dữ liệu theo `kid`), để
dựng ảnh chụp bucket cho máy mà không lưu bucket dạng rõ. Dòng thiếu `bucket_enc` không xuống máy; nạp lại tệp là bù.

    uv run --directory backend python -m hoicon.ops.threat_list load data/threat_seed.demo.json
    uv run --directory backend python -m hoicon.ops.threat_list unflag --h1-file <tệp> [--confirm]

Tệp theo `docs/schemas/threat_seed.v1.json` (đầu vào có h1 — với tệp demo là số hư cấu). Nạp lặp lại là cập nhật
(`ON CONFLICT`), không thêm dòng. Cả lô được kiểm trước khi ghi và ghi trong MỘT giao dịch: một dòng hỏng ⇒ không
ghi gì. Tệp `is_demo` CHỈ nạp được khi `HOICON_ENV` là dev/test/ci (danh sách trắng: quên đặt `prod` vẫn không
lọt). Chỉ in số dòng thêm/cập nhật và số dòng còn thiếu `bucket_enc` — không in h1, HMAC hay bucket.
"""

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, literal_column, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from hoicon.config import get_settings
from hoicon.db.models import ThreatIndicator
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import candidate_hmacs, hmac_h1
from hoicon.domain.threat_bucket import bucket24, encrypt_bucket

DEMO_ALLOWED_ENVS = ("dev", "test", "ci")
_H1 = re.compile(r"[0-9a-f]{64}")  # dùng `fullmatch`: `$` của `re` cho lọt "\n" ở cuối
_LAST3 = re.compile(r"[0-9]{3}")


class SeedError(ValueError):
    """Tệp nạp không hợp lệ. Thông điệp nêu số thứ tự chỉ báo + tên trường, không bao giờ nêu giá trị (có thể là h1)."""


def _text(item: dict[str, Any], key: str, index: int, *, required: bool, limit: int) -> str | None:
    value = item.get(key)
    if value is None and not required:
        return None
    if not isinstance(value, str) or not 1 <= len(value) <= limit:
        raise SeedError(f"chỉ báo #{index}: '{key}' phải là chuỗi dài 1–{limit} ký tự")
    return value


def _validate(doc: object, env: str) -> tuple[str, bool, list[dict[str, Any]]]:
    if not isinstance(doc, dict) or not isinstance(doc.get("indicators"), list):
        raise SeedError("tệp phải là đối tượng có 'version', 'is_demo', 'indicators'")
    version = doc.get("version")
    if not isinstance(version, str) or not 1 <= len(version) <= 32:
        raise SeedError("'version' phải là chuỗi dài 1–32 ký tự")
    is_demo = doc.get("is_demo")
    if not isinstance(is_demo, bool):
        raise SeedError("'is_demo' phải là true/false")
    if is_demo and env.strip().lower() not in DEMO_ALLOWED_ENVS:
        raise SeedError("từ chối: tệp demo (is_demo=true) chỉ nạp khi HOICON_ENV là dev, test hoặc ci")
    clean: list[dict[str, Any]] = []
    for index, item in enumerate(doc["indicators"], start=1):
        if not isinstance(item, dict):
            raise SeedError(f"chỉ báo #{index}: phải là đối tượng")
        h1 = item.get("h1")
        if not isinstance(h1, str) or not _H1.fullmatch(h1):
            raise SeedError(
                f"chỉ báo #{index}: 'h1' phải là SHA-256 hex chữ thường (64 ký tự), không phải số điện thoại"
            )
        confidence = item.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, int | float) or not 0 <= confidence <= 1:
            raise SeedError(f"chỉ báo #{index}: 'confidence' phải nằm trong [0, 1]")
        last3 = item.get("last3")
        if last3 is not None and not (isinstance(last3, str) and _LAST3.fullmatch(last3)):
            raise SeedError(f"chỉ báo #{index}: 'last3' phải đúng 3 chữ số")
        expires = item.get("expires_at")
        expires_at: datetime | None = None
        if expires is not None:
            try:
                expires_at = datetime.fromisoformat(expires)
            except (TypeError, ValueError):
                raise SeedError(f"chỉ báo #{index}: 'expires_at' phải là ngày giờ ISO 8601") from None
            if expires_at.tzinfo is None:
                raise SeedError(f"chỉ báo #{index}: 'expires_at' phải có múi giờ")
        clean.append(
            {
                "h1": h1,
                "source": _text(item, "source", index, required=True, limit=64),
                "confidence": confidence,
                "tactic": _text(item, "tactic", index, required=False, limit=64),
                "last3": last3,
                "expires_at": expires_at,
            }
        )
    return version, is_demo, clean


async def load_seed(
    sessions: async_sessionmaker, doc: object, *, env: str, with_bucket: bool = True
) -> tuple[int, int]:
    """Nạp `doc` ⇒ (số dòng thêm, số dòng cập nhật). Dùng chung với `hoicon-eval` (nạp danh sách demo vào DB eval).

    `with_bucket=False` (eval, không có khóa dữ liệu): không ghi và không đụng `bucket_enc` đã có.

    ponytail: một câu lệnh mỗi dòng — đủ cho danh sách thí điểm (≤ 100.000 dòng, nạp thủ công); gộp lô khi cần.
    """
    version, is_demo, indicators = _validate(doc, env)
    added = updated = 0
    async with sessions.begin() as session:  # một giao dịch: lỗi giữa chừng ⇒ không ghi dòng nào
        for item in indicators:
            kid, digest = hmac_h1(item["h1"])
            values = {
                "kind": "phone",
                "value_hmac": digest,
                "value_kid": kid,
                "last3": item["last3"],
                "source": item["source"],
                "confidence": item["confidence"],
                "tactic": item["tactic"],
                "list_version": version,
                "is_demo": is_demo,
                "expires_at": item["expires_at"],
            }
            update = {key: values[key] for key in ("source", "confidence", "tactic", "list_version", "last3")}
            if with_bucket:  # nonce ngẫu nhiên ⇒ mỗi lần nạp lại ra bản mã mới (cùng bucket)
                values["bucket_enc"] = update["bucket_enc"] = encrypt_bucket(bucket24(item["h1"]), digest)
            statement = (
                insert(ThreatIndicator)
                .values(**values)
                .on_conflict_do_update(
                    constraint="uq_threat_indicators_value",
                    set_={
                        **update,
                        "expires_at": values["expires_at"],
                        "is_demo": is_demo,
                        "last_seen": literal_column("now()"),
                    },
                )
                .returning(literal_column("(xmax = 0)"))
            )
            if await session.scalar(statement):
                added += 1
            else:
                updated += 1
    return added, updated


async def count_missing_bucket(sessions: async_sessionmaker) -> int:
    """Số chỉ báo chưa có `bucket_enc` (chưa xuống máy được cho tới khi nạp lại tệp có h1)."""
    query = select(func.count()).select_from(ThreatIndicator).where(ThreatIndicator.bucket_enc.is_(None))
    async with sessions() as session:
        return await session.scalar(query) or 0


async def run(path: Path) -> int:
    try:
        doc = json.loads(await asyncio.to_thread(path.read_text, encoding="utf-8"))
    except (OSError, ValueError) as exc:  # chỉ tên lớp lỗi: thông điệp JSON có thể trích lại nội dung tệp
        print(f"Từ chối: không đọc được tệp ({type(exc).__name__}).")
        return 2
    try:
        added, updated = await load_seed(get_sessionmaker(), doc, env=get_settings().env)
    except SeedError as exc:
        print(f"Từ chối: {exc}")
        return 2
    except RuntimeError as exc:  # thiếu khóa băm: thông điệp chỉ nêu TÊN biến môi trường
        print(f"Từ chối: {exc}")
        return 2
    except SQLAlchemyError as exc:  # không in thông điệp: có thể chứa chuỗi kết nối DB
        print(f"Lỗi cơ sở dữ liệu ({type(exc).__name__}) — kiểm tra Postgres và `alembic upgrade head`.")
        return 2
    print(f"Danh sách đe dọa: thêm {added} · cập nhật {updated}")
    try:
        missing = await count_missing_bucket(get_sessionmaker())
    except SQLAlchemyError as exc:  # không in thông điệp: có thể chứa chuỗi kết nối DB
        print(f"Lỗi cơ sở dữ liệu ({type(exc).__name__}) khi đếm dòng thiếu bucket_enc.")
        return 2
    print(f"Dòng thiếu bucket_enc: {missing}" + (" (nạp lại tệp có h1 để bù)" if missing else ""))
    return 0


MAX_UNFLAG = 10_000


def read_h1_file(path: Path) -> tuple[list[str], int]:
    """Đọc tệp mỗi dòng một h1 (SHA-256 hex 64 ký tự, chữ thường) ⇒ (h1 hợp lệ không trùng, số dòng sai định dạng).
    Dòng trống và dòng bắt đầu bằng `#` bị bỏ qua. Không bao giờ nêu nội dung dòng sai (có thể là số điện thoại thô)."""
    seen: dict[str, None] = {}
    bad = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if _H1.fullmatch(value):
            seen[value] = None
        else:
            bad += 1
    if len(seen) > MAX_UNFLAG:
        raise SeedError(f"tệp có quá {MAX_UNFLAG} h1")
    return list(seen), bad


async def unflag(sessions: async_sessionmaker, h1s: list[str]) -> tuple[int, int]:
    """Gỡ các số bị gắn cờ nhầm theo h1 (khớp HMAC theo mọi kid pepper) ⇒ (số h1 đã gỡ được, số h1 không thấy)."""
    removed = missing = 0
    async with sessions.begin() as session:  # một giao dịch: lỗi giữa chừng ⇒ không gỡ dòng nào
        for h1 in h1s:
            keys = candidate_hmacs(h1)
            result = await session.execute(
                delete(ThreatIndicator).where(
                    ThreatIndicator.kind == "phone",
                    tuple_(ThreatIndicator.value_kid, ThreatIndicator.value_hmac).in_(keys),
                )
            )
            if result.rowcount:
                removed += 1
            else:
                missing += 1
    return removed, missing


async def run_unflag(path: Path, *, confirm: bool) -> int:
    if not get_settings().is_dev_env and not confirm:
        print("Từ chối: ngoài dev/test/ci lệnh này cần thêm --confirm.")
        return 2
    try:
        h1s, bad = await asyncio.to_thread(read_h1_file, path)
    except (OSError, UnicodeDecodeError) as exc:  # chỉ tên lớp lỗi
        print(f"Từ chối: không đọc được tệp ({type(exc).__name__}).")
        return 2
    except SeedError as exc:
        print(f"Từ chối: {exc}")
        return 2
    if bad:
        print(f"Từ chối: {bad} dòng không phải h1 (SHA-256 hex 64 ký tự). Không gỡ gì.")
        return 2
    try:
        removed, missing = await unflag(get_sessionmaker(), h1s)
    except RuntimeError as exc:  # thiếu khóa băm: chỉ nêu TÊN biến môi trường
        print(f"Từ chối: {exc}")
        return 2
    except SQLAlchemyError as exc:
        print(f"Lỗi cơ sở dữ liệu ({type(exc).__name__}).")
        return 2
    print(f"Đã gỡ cờ: {removed} · không thấy: {missing}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("load", help="nạp (upsert) một tệp danh sách đe dọa").add_argument("path", type=Path)
    remover = sub.add_parser("unflag", help="gỡ số bị gắn cờ nhầm theo h1 trong tệp")
    remover.add_argument("--h1-file", required=True, type=Path)
    remover.add_argument("--confirm", action="store_true", help="bắt buộc ngoài dev/test/ci")
    args = parser.parse_args(argv)
    job = run(args.path) if args.cmd == "load" else run_unflag(args.h1_file, confirm=args.confirm)
    return asyncio.run(job, loop_factory=asyncio.SelectorEventLoop)  # psycopg async cần SelectorEventLoop


if __name__ == "__main__":
    sys.exit(main())
