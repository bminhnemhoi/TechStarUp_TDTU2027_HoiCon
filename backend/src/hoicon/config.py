from functools import lru_cache
from pathlib import Path
from typing import Literal

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
    web_base_url: str = "https://app.hoicon.vn"
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
    # Worker job chạy nền trong tiến trình API (ADR-002); false khi chạy worker ở tiến trình riêng.
    run_worker: bool = True
    gemini_api_key: SecretStr | None = None
    zalo_bot_token: SecretStr | None = None
    zalo_webhook_secret: SecretStr | None = None
    # `mock` (mặc định, CI/không token) | `live` (gọi Zalo thật; thiếu token ⇒ lỗi khi khởi động, không rơi về mock).
    zalo_mode: Literal["mock", "live"] = "mock"
    # Bot nhận webhook (một bot dev ở spike; 3 bot thí điểm sau: thêm khóa + token theo bot_id).
    zalo_bot_id: str = "hoicon-dev"
    # Hạn mức tin/tháng của gói Basic (bot.zapps.me, tra 15/10/2026) và ngưỡng cảnh báo/giữ tin không khẩn (% hạn mức).
    zalo_monthly_quota: int = 3000
    zalo_quota_warn_pct: int = 80
    zalo_quota_hold_pct: int = 95
    phone_pepper_kid: int = 1
    phone_pepper_1: SecretStr | None = None
    phone_pepper_2: SecretStr | None = None  # xoay pepper: kid cũ vẫn tra được (`candidate_hmacs`)
    # MCP `threat` (spec 003): tên client → SHA-256 hex của token (`python -m hoicon.ops.mcp_token new --client <tên>`).
    # Máy chủ không giữ token thô; rỗng ⇒ mọi yêu cầu bị 401 (đóng mặc định). Hạn mức đếm trong bộ nhớ (ADR-002).
    mcp_threat_clients: dict[str, str] = {}
    mcp_rate_per_min: int = 30
    mcp_rate_per_day: int = 1000
    # Khóa ký JWT thiết bị HS256 (spec 020, FR-004; ≥ 32 ký tự ngẫu nhiên, ví dụ `openssl rand -hex 32`). Thiếu/ngắn ⇒
    # /v1/pair trả 503 và mọi token bị từ chối (đóng mặc định). Đổi khóa = mọi thiết bị phải ghép đôi lại.
    device_jwt_secret: SecretStr | None = None
    # Khóa AES-256-GCM (hex 64 ký tự) mã hóa Zalo chat_id (spec 002 D1); kid để xoay khóa.
    data_key_kid: int = 1
    data_key_1: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
