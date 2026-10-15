# Kế hoạch kỹ thuật: Spec 022 — Sentinel v1 (Android)

**Mã**: `specs/022-sentinel-v1/plan.md` · **Làn A (Android)**

---

## 1. Kiến trúc CSDL Room & Lưu trữ an toàn

### Thư mục: `apps/android/app/src/main/java/vn/hoicon/sentinel/data/local/`
- `SentinelDatabase.kt`: Room database phiên bản 1 (không cho phép export schema lúc này hoặc export vào `schemas/`).
- Bảng `OutboxEventEntity`:
  - `id`: String (UUIDv7) - Primary Key
  - `payloadJsonEncrypted`: String (chuỗi JSON sự kiện mã hóa bằng Tink AEAD)
  - `status`: String (`PENDING`, `SENDING`, `SENT`, `FAILED`)
  - `retryCount`: Int
  - `createdAt`: Long
- Bảng `ThreatHashEntity`:
  - `h1`: String (Primary Key)
  - `last3`: String
  - `version`: String
- Bảng `RiskWindowState`:
  - `id`: Int (Primary Key = 1, singleton)
  - `isOpen`: Boolean
  - `openedAt`: Long
  - `callerH1`: String?
  - `callerLast3`: String?
  - `expiresAt`: Long

---

## 2. Quản lý cửa sổ rủi ro & Luật cục bộ

### Thư mục: `apps/android/app/src/main/java/vn/hoicon/sentinel/domain/rules/`
- `RiskWindowManager.kt`:
  - Cửa sổ rủi ro mở khi kết thúc cuộc gọi lạ (`onCallEnded` từ `CallScreeningService` hoặc BroadcastReceiver).
  - Kéo dài 600 giây (10 phút).
- `LocalRulesEvaluator.kt`:
  - Kiểm tra sự kiện tiền cảnh (`UsageEvents`):
    - App ngân hàng (`bank_apps.vn.json`) $\rightarrow$ Kích hoạt Luật R1 (`rule_floor = high`).
    - App điều khiển từ xa (`AnyDesk`, `UltraViewer`, `TeamViewer`) $\rightarrow$ Kích hoạt Luật R5 (`rule_floor = critical`).
  - Sinh sự kiện `RiskEvent` ghi vào Outbox và kích hoạt SafePauseActivity / Overlay.

---

## 3. Giao diện Compose (E6 & E7)

### Thư mục: `apps/android/app/src/main/java/vn/hoicon/sentinel/ui/`
- `ProtectionStatusScreen.kt` (E6):
  - Biểu tượng lá chắn xanh từ `Tokens.kt` (`brand.green_text` / `risk.low.fg`).
  - Font Be Vietnam Pro, kích thước chữ $\ge 20$sp.
  - Nút "Hỏi con" kích thước $\ge 64$dp gọi trực tiếp hoặc gửi tín hiệu cần trợ giúp.
- `SafePauseScreen.kt` (E7):
  - Nền cảnh báo `brand.orange` / `risk.high.accent`.
  - Đồng hồ đếm ngược 60 giây.
  - Câu nhắc: "Hỏi người gọi mật khẩu gia đình" (I2).
  - Nút "Hủy giao dịch" màu đỏ/cam đậm, nút "Tiếp tục" cần xác nhận hoặc chờ hết thời gian.
  - Nút "Nghe lại" gọi Android TextToSpeech ngoại tuyến.

---

## 4. Công nhân nền (Workers)

- `OutboxWorker.kt`:
  - Kích hoạt khi có kết nối mạng (`NetworkType.CONNECTED`).
  - Đọc các sự kiện `PENDING` từ `OutboxEventEntity`.
  - Giải mã Tink, đóng gói mảng JSON và gọi `PairingApiClient.sendEvents(events)`.
  - Đánh dấu `SENT` hoặc tăng `retryCount`.
- `HeartbeatWorker.kt`:
  - Chạy chu kỳ 15 phút, gửi ping trạng thái bảo vệ.
