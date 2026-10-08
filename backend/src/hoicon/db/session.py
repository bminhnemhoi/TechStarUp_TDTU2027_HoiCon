from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from hoicon.config import get_settings

# Không có connect_timeout, psycopg async trên Windows chờ mãi khi Postgres từ chối kết nối (DB tắt/khởi động lại)
# ⇒ /readyz và test treo. psycopg áp dụng timeout cho TỪNG địa chỉ: host "localhost" (::1 + 127.0.0.1) ⇒ tối đa ~2×.
# /readyz còn có trần riêng (READYZ_TIMEOUT_S). 5 s đủ cho DB cùng máy/cùng mạng nội bộ.
CONNECT_TIMEOUT_S = 5


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(
        get_settings().database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=5,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_S},
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker:
    return async_sessionmaker(get_engine(), expire_on_commit=False)
