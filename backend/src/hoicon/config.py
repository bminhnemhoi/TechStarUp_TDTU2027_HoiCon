from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cấu hình đọc từ biến môi trường / backend/.env (tên biến xem .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="HOICON_", extra="ignore")

    env: str = "dev"
    # Dev DB từ infra/compose.dev.yml (chỉ bind 127.0.0.1, không phải bí mật). Prod đặt HOICON_DATABASE_URL.
    database_url: str = "postgresql+psycopg://hoicon:hoicon_dev@127.0.0.1:15432/hoicon"


@lru_cache
def get_settings() -> Settings:
    return Settings()
