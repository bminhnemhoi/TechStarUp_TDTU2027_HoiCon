from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Cấu hình đọc từ biến môi trường / backend/.env (tên biến xem .env.example).

    Bí mật là SecretStr: repr/log chỉ hiện '**********'. Lấy giá trị thật bằng .get_secret_value() ngay tại chỗ dùng
    (tạo engine, gọi API), không gán ra biến sống lâu. Đường dẫn .env tuyệt đối ⇒ chạy từ thư mục nào cũng đúng file.
    """

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_prefix="HOICON_", extra="ignore")

    env: str = "dev"
    # Dev DB từ infra/compose.dev.yml (chỉ bind 127.0.0.1, không phải bí mật). Prod: HOICON_DATABASE_URL có mật khẩu.
    database_url: SecretStr = SecretStr("postgresql+psycopg://hoicon:hoicon_dev@127.0.0.1:15432/hoicon")

    anthropic_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    zalo_bot_token: SecretStr | None = None
    zalo_webhook_secret: SecretStr | None = None
    phone_pepper_kid: int = 1
    phone_pepper_1: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
