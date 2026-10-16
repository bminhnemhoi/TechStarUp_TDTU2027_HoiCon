"""Ảnh chụp danh sách đe dọa cho máy (spec 026 FR-009, ADR-011): các bucket k-ẩn danh, KHÔNG phải tập h1.

Dựng từ `threat_indicators.bucket_enc` (giải mã bằng khóa dữ liệu ngoài DB): dịch về `bucket_bits` bit đầu, bỏ trùng,
sắp xếp, đóng gói 3 byte/bucket (uint24 big-endian). `version = sha256(bits ‖ nội dung)[:16]` nên nạp lại cùng danh sách
(bản mã mới, cùng bucket) KHÔNG đổi phiên bản ⇒ máy nhận 304. Phản hồi không có h1, HMAC hay last3.

Dòng bị loại: hết hạn; thiếu `bucket_enc` (chưa nạp lại sau migration 0007); không giải mã được (khóa sai/dữ liệu hỏng:
bỏ qua và đếm, không làm hỏng cả danh sách); dòng `is_demo` ở mọi môi trường ngoài dev/test/ci (bản prod không phát số
hư cấu xuống máy thật). Bộ nhớ đệm trong tiến trình 5 phút (ADR-002): danh sách đằng nào cũng phát cho mọi máy.
"""

import asyncio
import hashlib
import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hoicon.db.models import ThreatIndicator
from hoicon.domain.threat_bucket import decrypt_bucket, shift
from hoicon.ops.threat_list import DEMO_ALLOWED_ENVS

logger = logging.getLogger(__name__)

CACHE_TTL_S = 300
BUCKET_BYTES = 3


@dataclass(frozen=True)
class Snapshot:
    version: str
    bucket_bits: int
    count: int
    buckets: bytes  # count × 3 byte, đã sắp xếp, không trùng
    generated_at: datetime


def include_demo(env: str) -> bool:
    """Chỉ dev/test/ci được phát chỉ báo `is_demo` (cùng danh sách trắng với `ops.threat_list`)."""
    return env.strip().lower() in DEMO_ALLOWED_ENVS


def pack(values: Iterable[int]) -> bytes:
    return b"".join(value.to_bytes(BUCKET_BYTES, "big") for value in sorted(set(values)))


def make_snapshot(bits: int, values: Iterable[int]) -> Snapshot:
    packed = pack(values)
    version = hashlib.sha256(bytes([bits]) + packed).hexdigest()[:16]
    return Snapshot(version, bits, len(packed) // BUCKET_BYTES, packed, datetime.now(UTC))


def empty_snapshot(bits: int) -> Snapshot:
    return make_snapshot(bits, [])


async def build_snapshot(session: AsyncSession, bits: int, *, demo: bool) -> Snapshot:
    query = select(ThreatIndicator.value_hmac, ThreatIndicator.bucket_enc).where(
        ThreatIndicator.kind == "phone",
        ThreatIndicator.bucket_enc.is_not(None),
        or_(ThreatIndicator.expires_at.is_(None), ThreatIndicator.expires_at > func.now()),
    )
    if not demo:
        query = query.where(ThreatIndicator.is_demo.is_(False))
    rows = [(value_hmac, bucket_enc) for value_hmac, bucket_enc in (await session.execute(query)).all()]
    buckets, skipped = await asyncio.to_thread(_decode_rows, rows, bits)  # N lần AES-GCM: không chặn event loop
    if skipped:
        logger.warning("threat-list: bỏ %d chỉ báo không giải mã được bucket_enc", skipped)
    return make_snapshot(bits, buckets)


def _decode_rows(rows: list[tuple[str, str]], bits: int) -> tuple[set[int], int]:
    buckets: set[int] = set()
    skipped = 0
    for value_hmac, bucket_enc in rows:
        try:
            buckets.add(shift(decrypt_bucket(bucket_enc, value_hmac), bits))
        except ValueError:  # bản mã hỏng/bị tráo: bỏ dòng, không lộ gì (thông điệp đã rỗng dữ liệu)
            skipped += 1
    return buckets, skipped


_cache: dict[tuple[int, bool], tuple[float, Snapshot]] = {}
_locks: dict[tuple[int, bool], asyncio.Lock] = {}  # single-flight: hết hạn cache thì chỉ MỘT request dựng lại


def _now() -> float:
    return time.monotonic()


def reset_cache() -> None:
    _cache.clear()
    _locks.clear()


async def get_snapshot(sessions: async_sessionmaker, bits: int, env: str) -> Snapshot:
    demo = include_demo(env)
    now = _now()
    cached = _cache.get((bits, demo))
    if cached is not None and now - cached[0] < CACHE_TTL_S:
        return cached[1]
    async with _locks.setdefault((bits, demo), asyncio.Lock()):
        cached = _cache.get((bits, demo))
        if cached is not None and _now() - cached[0] < CACHE_TTL_S:  # request trước đã dựng xong trong lúc ta chờ
            return cached[1]
        async with sessions() as session:
            snapshot = await build_snapshot(session, bits, demo=demo)
        _cache[(bits, demo)] = (_now(), snapshot)
        return snapshot
