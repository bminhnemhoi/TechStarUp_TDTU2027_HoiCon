"""Sinh mã ghép Zalo 6 số cho gia đình dev/demo (FR-004; luồng ghép từ app thuộc spec 020):

    uv run --directory backend python -m hoicon.ops.pairing_code --family dev-gia-dinh

Gia đình chưa có thì được tạo (luôn `is_demo`); gia đình thật bị từ chối. Mã chỉ lưu băm, hết hạn sau 15 phút, dùng một
lần. Mã in ra là mã dùng-một-lần để người dùng nhắn cho bot, không phải khóa dịch vụ.
"""

import argparse
import asyncio
import secrets
import sys
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from hoicon.config import get_settings
from hoicon.db.models import Family, PairingCode
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import hmac_pairing_code

CODE_TTL = timedelta(minutes=15)
MAX_NAME = 64


async def create_pairing_code(sessions: async_sessionmaker, family_id: object) -> str:
    for _ in range(20):  # trùng băm với một mã chưa dùng khác (chỉ số unique) ⇒ bốc lại
        code = f"{secrets.randbelow(10**6):06d}"
        try:
            async with sessions.begin() as session:
                session.add(
                    PairingCode(
                        family_id=family_id, code_hash=hmac_pairing_code(code), expires_at=func.now() + CODE_TTL
                    )
                )
        except IntegrityError:
            continue
        return code
    raise RuntimeError("không sinh được mã ghép không trùng")


async def run(name: str) -> int:
    if get_settings().env != "dev":
        print("Từ chối: lệnh này chỉ chạy khi HOICON_ENV=dev (mã ghép cho gia đình thật sinh từ app, spec 020).")
        return 2
    sessions = get_sessionmaker()
    async with sessions.begin() as session:
        query = select(Family).where(Family.display_name == name).order_by(Family.created_at)
        family = (await session.scalars(query)).first()
        if family is None:
            family = Family(display_name=name, region="nam", is_demo=True)
            session.add(family)
        elif not family.is_demo:
            print("Từ chối: đây là gia đình thật — mã ghép cho gia đình thật phải sinh từ app (spec 020).")
            return 2
    async with sessions.begin() as session:  # mỗi gia đình chỉ một mã còn hiệu lực: giảm bề mặt dò mã 6 số
        await session.execute(
            delete(PairingCode).where(PairingCode.family_id == family.id, PairingCode.used_at.is_(None))
        )
    code = await create_pairing_code(sessions, family.id)
    print(f"Gia đình dev: {name} (id {family.id})")
    print(f"Mã ghép đôi: {code} — dùng một lần, hết hạn sau 15 phút. Nhắn cho bot Zalo: /start {code}")
    return 0


def _name(value: str) -> str:
    if not 1 <= len(value) <= MAX_NAME:
        raise argparse.ArgumentTypeError(f"tên gia đình dài 1–{MAX_NAME} ký tự")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--family", required=True, type=_name, help="tên (bí danh) gia đình dev; chưa có thì tạo")
    args = parser.parse_args(argv)
    return asyncio.run(run(args.family), loop_factory=asyncio.SelectorEventLoop)  # psycopg async cần SelectorEventLoop


if __name__ == "__main__":
    sys.exit(main())
