# Tuân thủ chính sách Google Play

> Trạng thái: **khung** (P0-05) — cập nhật mỗi khi đổi `AndroidManifest.xml`. Hook `guard-privacy` chặn quyền bị cấm.

| Quyền / API | Mục đích | Khai báo Play | Trạng thái |
|---|---|---|---|
| Vai trò `CALL_SCREENING` | gắn nhãn cuộc gọi, biết số lạ | — (vai trò người dùng cấp) | dự kiến |
| `READ_PHONE_STATE` (nếu P1-S1 chọn `TelephonyCallback`) | biết đang trong cuộc gọi | — | chờ P1-S1 |
| `PACKAGE_USAGE_STATS` (quyền đặc biệt) | biết app ngân hàng lên tiền cảnh trong cửa sổ rủi ro | giải trình trong Data safety | dự kiến |
| `SYSTEM_ALERT_WINDOW` | mở SafePause từ nền (miễn trừ BAL) — **không vẽ đè app ngân hàng** | — | dự kiến |
| `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_SPECIAL_USE` | cửa sổ rủi ro ≤ 10 phút | khai báo FGS specialUse + video | dự kiến |
| `POST_NOTIFICATIONS`, `INTERNET` | thông báo, đồng bộ | — | dự kiến |
| `<queries>` các gói ngân hàng | thay cho `QUERY_ALL_PACKAGES` | — | dự kiến |

**Đã kiểm (P0-06, `aapt2 dump badging`):** manifest gộp của bản khung chỉ có
`vn.hoicon.sentinel.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION` — quyền nội bộ mức signature do androidx.core tự thêm,
không phải quyền người dùng cấp. `allowBackup="false"` + `dataExtractionRules` loại trừ toàn bộ dữ liệu (Android 12+
vẫn chuyển dữ liệu máy-sang-máy nếu chỉ đặt `allowBackup`).

**Cấm** (không bao giờ khai báo): SMS, nhật ký cuộc gọi, danh bạ, `QUERY_ALL_PACKAGES`, `REQUEST_INSTALL_PACKAGES`,
Accessibility, Notification Listener, ghi âm cuộc gọi.

Cần chuẩn bị: Data safety form, chính sách quyền riêng tư công khai (`/privacy`), video minh họa FGS specialUse, tài
khoản thử cho reviewer, closed testing qua Google Group (ADR-005).
