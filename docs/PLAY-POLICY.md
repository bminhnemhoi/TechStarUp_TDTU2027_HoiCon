# Tuân thủ chính sách Google Play

> Cập nhật mỗi khi đổi `AndroidManifest.xml`. Hook `guard-privacy` chặn quyền bị cấm. Cơ chế chốt: **ADR-007**.

| Quyền / API | Mục đích | Khai báo Play | Trạng thái |
|---|---|---|---|
| Vai trò `CALL_SCREENING` | biết cuộc gọi từ **số lạ** (hệ thống chỉ gọi `onScreenCall` cho số không có trong danh bạ), gắn nhãn số bị gắn cờ | — (vai trò người dùng cấp) | **đang dùng** (P1-S1) |
| ~~`READ_PHONE_STATE`~~ | ~~trạng thái cuộc gọi~~ | — | **không dùng** — `AudioManager.mode` đủ (ADR-007) |
| `PACKAGE_USAGE_STATS` (quyền đặc biệt) | biết app tài chính lên tiền cảnh **chỉ trong cửa sổ rủi ro ≤ 10 phút** | giải trình trong Data safety + mô tả trong app | **đang dùng** |
| `SYSTEM_ALERT_WINDOW` | **chỉ** để được mở SafePause từ nền (miễn trừ BAL) — **không vẽ overlay**, không đè app ngân hàng | — | **đang dùng** |
| `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_SPECIAL_USE` | cửa sổ rủi ro ≤ 10 phút sau cuộc gọi số lạ; property `PROPERTY_SPECIAL_USE_FGS_SUBTYPE` mô tả mục đích | **khai báo FGS specialUse + video minh họa** trong Play Console | **đang dùng** |
| Miễn tối ưu pin (người dùng tự đặt "Không giới hạn") | Android 15+ không cho mở FGS từ nền nếu thiếu (đã đo trên API 36) | **không** dùng quyền `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` — mở màn danh sách cài đặt pin (`ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS`) | **đang dùng** (onboarding E3) |
| `POST_NOTIFICATIONS` | thông báo "HỏiCon đang bảo vệ" + thông báo dự phòng khi SafePause không hiện | — | **đang dùng** |
| `HIDE_OVERLAY_WINDOWS` (quyền thường) | ẩn lớp phủ của app khác khi SafePause hiện — chống app độc che màn/lừa bấm "tiếp tục" (tapjacking) | — | **đang dùng** (review bảo mật 09/10) |
| `INTERNET` | đồng bộ sự kiện / cảnh báo người giám hộ (ngoài đường găng) | Data safety | từ P2-03 (bản spike không có) |
| `<queries>` các gói tài chính | thay cho `QUERY_ALL_PACKAGES`; khớp **đúng tên gói** `data/bank_apps.vn.json` | — | **đang dùng** (9 gói ở spike; đủ danh sách ở P1-S2) |

**Đã kiểm (P1-S1, `aapt2 dump badging` APK debug 09/10):** chỉ có 6 quyền trên + quyền nội bộ androidx
`vn.hoicon.sentinel.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION` (mức signature, không phải quyền người dùng cấp).
`allowBackup="false"` + `dataExtractionRules` loại trừ toàn bộ dữ liệu (Android 12+ vẫn chuyển dữ liệu máy-sang-máy nếu
chỉ đặt `allowBackup`).

**Cấm** (không bao giờ khai báo): SMS, nhật ký cuộc gọi, danh bạ, `QUERY_ALL_PACKAGES`, `REQUEST_INSTALL_PACKAGES`,
Accessibility, Notification Listener, ghi âm cuộc gọi, `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`.

Cần chuẩn bị (P1-08): Data safety form, chính sách quyền riêng tư công khai (`/privacy`), video minh họa FGS specialUse
(quay trên máy ảo: cuộc gọi lạ → mở app ngân hàng mẫu → màn dừng an toàn), tài khoản thử cho reviewer, closed testing qua
Google Group (ADR-005).
