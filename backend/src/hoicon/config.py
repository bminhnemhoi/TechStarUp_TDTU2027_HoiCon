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
    # Hồ sơ `fast` của llm_router (P1-S4 so Haiku 4.5 với Haiku 5.5; Gemini Flash-Lite khi có khóa).
    llm_fast_model: str = "claude-haiku-5-5"
    llm_daily_budget_usd: float = 2.0
    # Bộ hẹn giờ của đồ thị sự cố (giây): hỏi người cao tuổi; T1 nhắc, T2 chuyển người giám hộ 2, T3 dừng chờ.
    timer_ask_elder_s: int = 60
    timer_t1_s: int = 120
    timer_t2_s: int = 300
    timer_t3_s: int = 900
    gemini_api_key: SecretStr | None = None
    zalo_bot_token: SecretStr | None = None
    zalo_webhook_secret: SecretStr | None = None
    phone_pepper_kid: int = 1
    phone_pepper_1: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
