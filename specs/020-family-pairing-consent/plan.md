# Technical Implementation Plan: Spec 020 — Ghép đôi gia đình & Sổ đồng ý bất biến

**Mã ROADMAP**: P2-01 + P2-02 · **Làn**: A (Android) + B (Server) · **Ngày lập**: 15/10/2026

## 1. Quyết định kiến trúc & Kỹ thuật

### Quyết định 1 (T1) — Sổ đồng ý bất biến bằng PostgreSQL Trigger cấp cơ sở dữ liệu
- **Vấn đề**: Hiến chương và Nghị định 356/2025 yêu cầu nhật ký đồng ý không thể bị sửa chữa hay xóa bỏ (append-only), nhằm chống chối bỏ trong các cuộc điều tra sự cố lừa đảo. Nếu chỉ dựa vào mã ứng dụng (FastAPI) thì lỗi logic hoặc quyền truy cập DB trực tiếp có thể làm mất dữ liệu.
- **Giải pháp**: Tạo trigger function `prevent_consent_tamper()` ngay trong migration `0005`. Trigger gắn sự kiện `BEFORE UPDATE OR DELETE ON consents` cho từng dòng và lập tức `RAISE EXCEPTION`. Bất kỳ hành động rút quyền nào trong tương lai chỉ được phép ghi thêm một dòng mới với `granted = false`.

### Quyết định 2 (T2) — Cơ chế JWT Thiết bị (`DeviceAuth`) độc lập
- **Vấn đề**: Thiết bị của cha mẹ hoạt động liên tục trong nền (Foreground Service) để phát hiện cuộc gọi lạ và gửi sự cố khẩn cấp, không thể bắt người già đăng nhập lại hằng ngày.
- **Giải pháp**:
  - `access_token`: JWT chứa `device_id`, `family_id`, `member_id`, `role: "protected"`. Thời hạn 30 ngày. Ký bằng HMAC-SHA256 với khóa bí mật cấu hình `HOICON_DEVICE_JWT_SECRET`.
  - `refresh_token`: Chuỗi ngẫu nhiên bảo mật 32 bytes (`secrets.token_urlsafe(32)`), chỉ lưu băm SHA-256 (`device_secret_hash`) trong bảng `devices`. Dùng để cấp lại access token khi cần.

### Quyết định 3 (T3) — Tra cứu mã ghép đôi nguyên tử (Atomic Pairing Transaction)
- **Vấn đề**: Hai thiết bị nhập cùng một mã 6 số cùng lúc có thể gây tranh chấp tạo 2 thiết bị vào cùng 1 mã.
- **Giải pháp**:
  - Dùng câu lệnh `SELECT ... FROM pairing_codes WHERE code_hash = :hash AND used_at IS NULL AND expires_at > now() FOR UPDATE`.
  - Cập nhật ngay `used_at = now()` và `INSERT INTO devices` trong cùng một giao dịch cơ sở dữ liệu.

### Quyết định 4 (T4) — Luồng Onboarding Android E1–E4 tuân thủ Google Play Policy
- **Vấn đề**: Google Play kiểm duyệt cực kỳ gắt gao các ứng dụng sử dụng quyền `Accessibility`, `UsageStats` hoặc `CallScreening`. Nếu app hiện hộp thoại xin quyền của hệ điều hành mà không có màn hình giải thích trước (Prominent Disclosure) thì app sẽ bị từ chối phát hành ngay lập tức.
- **Giải pháp**:
  - Bố trí thứ tự chặt chẽ: `Welcome (E1)` → `Nhập mã 6 số (E2)` → `Công bố nổi bật Prominent Disclosure (E3)` → `Cấp quyền hệ thống (E4)`.
  - Màn E3 hiển thị đầy đủ: (1) Mục đích sử dụng quyền trợ năng & theo dõi app, (2) Cam kết KHÔNG thu thập mật khẩu, OTP, tin nhắn riêng tư, (3) Chỉ kích hoạt khi có cuộc gọi lạ.

---

## 2. Thiết kế chi tiết cơ sở dữ liệu (Migration 0005)

```sql
-- 1. Bảng devices
CREATE TABLE devices (
    id UUID PRIMARY KEY,
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    member_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    platform VARCHAR(16) NOT NULL DEFAULT 'android' CHECK (platform IN ('android', 'ios', 'web')),
    app_version VARCHAR(32) NOT NULL,
    rules_version VARCHAR(32) NOT NULL,
    threat_list_version VARCHAR(32),
    permission_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    fcm_token_enc TEXT,
    device_secret_hash CHAR(64) NOT NULL,
    last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_devices_family ON devices(family_id);

-- 2. Bảng consents
CREATE TABLE consents (
    id UUID PRIMARY KEY,
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    member_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    purpose VARCHAR(32) NOT NULL CHECK (purpose IN (
        'core_protection', 'call_screening', 'usage_monitoring', 'overlay_pause',
        'guardian_alerts', 'llm_processing', 'voice_input', 'drills', 'pilot_research'
    )),
    granted BOOLEAN NOT NULL,
    consent_version VARCHAR(16) NOT NULL,
    text_sha256 CHAR(64) NOT NULL,
    channel VARCHAR(16) NOT NULL CHECK (channel IN ('app', 'zalo', 'web')),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_consents_member ON consents(member_id, recorded_at);

-- Trigger chống sửa/xóa bảng consents
CREATE OR REPLACE FUNCTION prevent_consent_tamper()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'consents table is append-only: updates and deletes are prohibited for audit integrity';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_consents_immutable
BEFORE UPDATE OR DELETE ON consents
FOR EACH ROW
EXECUTE FUNCTION prevent_consent_tamper();

-- 3. Bảng trusted_contacts
CREATE TABLE trusted_contacts (
    id UUID PRIMARY KEY,
    family_id UUID NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    member_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    phone_hmac CHAR(64) NOT NULL,
    phone_kid SMALLINT NOT NULL,
    last3 CHAR(3),
    label VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_trusted_contacts_hmac ON trusted_contacts(phone_kid, phone_hmac);

-- 4. Bảng action_tokens
CREATE TABLE action_tokens (
    id UUID PRIMARY KEY,
    incident_id UUID,
    member_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    scope VARCHAR(32) NOT NULL CHECK (scope IN ('incident_decision', 'guardian_view', 'drill_debrief')),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_action_tokens_hash ON action_tokens(token_hash) WHERE used_at IS NULL;
```

---

## 3. Thiết kế API Endpoints (Làn B)

1. `POST /v1/pair`
   - Nhận payload theo schema `pair_request.v1.json`.
   - Tìm mã trong `pairing_codes`. Nếu không có / hết hạn 15' / đã dùng $\rightarrow$ trả `400 Bad Request` (`{"detail": "Mã ghép đôi không tồn tại hoặc đã hết hạn"}`).
   - Sinh UUIDv7 cho `device_id`.
   - Lưu vào `devices`.
   - Trả payload theo schema `pair_response.v1.json`.

2. `POST /v1/consents`
   - Bắt buộc header: `Authorization: Bearer <device_jwt>`.
   - Nhận payload theo schema `consent_record.v1.json`.
   - Chèn từng phần tử vào bảng `consents` với `family_id` và `member_id` lấy từ token.
   - Trả về `{"status": "recorded", "count": N, "recorded_at": "<ISO-timestamp>"}`.

---

## 4. Thiết kế Luồng UI Android (Làn A)

- **Entry point**: Kiểm tra `TokenStorage.hasValidToken()` trong `MainActivity.kt`.
  - Nếu đã có token $\rightarrow$ chuyển thẳng vào màn hình chính / `SafePauseScreen`.
  - Nếu chưa có $\rightarrow$ mở luồng `OnboardingActivity` (E1 $\rightarrow$ E2 $\rightarrow$ E3 $\rightarrow$ E4).
- **Màn hình E1 (Welcome)**:
  - Header: Logo HỏiCon + khẩu hiệu "Bảo vệ bình an cho gia đình".
  - Thân bài: Giải thích ngắn gọn: Con cái sẽ hỗ trợ canh chừng khi có số lạ gọi đến.
  - Nút chính: "Bắt đầu ghép đôi" (màu `BrandNavy`, cao 64dp, font Be Vietnam Pro Bold).
- **Màn hình E2 (Pairing)**:
  - Tiêu đề: "Nhập mã kết nối từ con".
  - Ô nhập 6 số: Cỡ chữ 32sp, căn giữa, tự động focus.
  - Nút bấm: "Kết nối gia đình" (màu `BrandNavy`).
  - Gọi `PairingClient.pair(code)`. Khi thành công, lưu token và chuyển sang E3.
- **Màn hình E3 (Prominent Disclosure)**:
  - Tiêu đề: "Cam kết minh bạch & quyền riêng tư".
  - Liệt kê 3 cam kết: (1) Chỉ bảo vệ khi có số lạ gọi tới, (2) Không nghe lén, không ghi âm cuộc gọi, (3) Không chia sẻ dữ liệu với bên thứ ba.
  - Nút "Tôi hiểu và tiếp tục" $\rightarrow$ chuyển sang E4.
- **Màn hình E4 (Permissions)**:
  - Giao diện cấp quyền trực quan, từng bước.
  - Sau khi người dùng cấp quyền, tự động gọi API `POST /v1/consents` gửi các bản ghi đồng ý lên server.
