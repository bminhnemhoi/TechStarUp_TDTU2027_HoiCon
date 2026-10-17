# Spec 022: Lính gác v1 — Cửa sổ rủi ro, Hàng đợi an toàn & Giao diện bảo vệ (Sentinel v1)

**Mã ROADMAP**: `P2-05` + `P2-06` · **Làn sở hữu**: Làn A (Android) · **Phụ thuộc**: `001-safe-pause-real-device`, `020-family-pairing-consent` · **Nhánh tính năng**: `feat/022-sentinel-v1`

---

## 1. Mục tiêu & Bối cảnh

Spec 022 hiện thực bộ não Lính gác (Sentinel) v1 trên Android:
1. Quản lý cửa sổ rủi ro (Risk Window) 600 giây sau cuộc gọi lạ và kích hoạt luật tất định R1 (app ngân hàng) & R5 (app điều khiển từ xa — ý tưởng I1).
2. Hàng đợi sự kiện gửi đi an toàn (Outbox) dùng Room Database kết hợp mã hóa Tink, tự động gửi lại sự kiện lên `POST /v1/events` khi có mạng.
3. Màn hình E6 "Đang bảo vệ" (Compose) và màn hình E7 SafePause hoàn chỉnh kết nối với luồng cảnh báo, hỗ trợ TTS offline và câu nhắc mật khẩu gia đình (ý tưởng I2).
4. Hoàn toàn độc lập với máy chủ: SafePause vẫn hiển thị $\le 3$ giây ngay cả khi máy ngoại tuyến (offline) hoặc máy chủ tắt.

---

## 2. Tiêu chí thành công (Success Criteria)

- **(SC-001)**: Độ trễ kích hoạt SafePause p95 $\le 3$ giây từ khi app ngân hàng lên tiền cảnh trong cửa sổ rủi ro; 100% hiển thị thành công khi tắt backend hoặc ngắt kết nối mạng.
- **(SC-002)**: Hàng đợi Outbox lưu trữ sự kiện mã hóa bằng Tink trong Room DB (`sentinel.db`); tự động gửi lại khi có mạng mà không mất sự kiện (0 lost events).
- **(SC-003)**: Màn hình E6 "Đang bảo vệ" và E7 SafePause tuân thủ 100% WCAG AAA $\ge 7:1$, dùng font Be Vietnam Pro, 0 mã màu hex lạ ngoài `Tokens.kt`, kích thước vùng chạm $\ge 64$dp.
- **(SC-004)**: Tích hợp ý tưởng I1 (Luật R5 phát hiện AnyDesk/UltraViewer/TeamViewer trong cửa sổ rủi ro) và I2 (nhắc "Hỏi người gọi mật khẩu gia đình" ở E7 mà không lưu mật khẩu trên máy).
- **(SC-005)**: Tuyệt đối 0 số điện thoại thô lưu trong Room DB hay logcat (`PiiMasker` bảo vệ 100% dữ liệu).
- **(SC-006)**: Cổng chất lượng: Gradle `:rules:test`, `:app:testDebugUnitTest`, `:app:lintDebug` 0 lỗi, `:app:assembleDebug` và `:app:processReleaseMainManifest` không có quyền cấm.

---

## 3. Yêu cầu chức năng (Functional Requirements)

- **(FR-001)**: Khởi tạo CSDL Room `sentinel.db` với bảng `outbox_events`, `risk_window_state`, `threat_hashes` kết hợp mã hóa Tink AEAD cho nội dung nhạy cảm.
- **(FR-002)**: Hiện thực `OutboxRepository` và `OutboxWorker` (WorkManager / Coroutines): quản lý hàng đợi gửi lại sự kiện lên `POST /v1/events` kèm cơ chế lũy tiến thời gian chờ (exponential backoff).
- **(FR-003)**: Hiện thực `RiskWindowManager`: kích hoạt cửa sổ rủi ro 600 giây khi kết thúc cuộc gọi từ số lạ (không có trong danh bạ và không thuộc liên hệ tin cậy).
- **(FR-004)**: Hiện thực bộ đánh giá luật cục bộ (Local Rules Engine):
  - **Luật R1**: Mở app ngân hàng / ví điện tử trong cửa sổ rủi ro $\rightarrow$ kích hoạt SafePause mức `high`.
  - **Luật R5 (I1)**: Mở app điều khiển từ xa (AnyDesk, UltraViewer, TeamViewer) trong cửa sổ rủi ro $\rightarrow$ kích hoạt SafePause mức `critical`.
- **(FR-005)**: Thiết kế màn hình E6 `ProtectionStatusScreen.kt` (Compose): giao diện hiển thị trạng thái "Đang bảo vệ", thẻ liên hệ gia đình, nút "Hỏi con" nổi bật $\ge 64$dp.
- **(FR-006)**: Thiết kế màn hình E7 `SafePauseScreen.kt` (Compose): hiển thị thông điệp cảnh báo rõ ràng, đếm ngược giữ an toàn, nút "Hủy giao dịch" & "Tôi muốn tiếp tục", nhắc nhở mật khẩu gia đình (I2).
- **(FR-007)**: Tích hợp Text-To-Speech (TTS) tiếng Việt ngoại tuyến đọc cảnh báo tự động khi SafePause kích hoạt, có nút "Nghe lại" $\ge 64$dp.
- **(FR-008)**: Hiện thực `HeartbeatWorker`: định kỳ 15 phút gửi trạng thái sức khỏe app (quyền, phiên bản) lên máy chủ khi có mạng.
- **(FR-009)**: Hiện thực `PiiMasker`: che số điện thoại (chỉ để lại 3 số cuối), băm `h1` theo chuẩn ADR-006, loại trừ mọi rò rỉ PII trong logcat.
- **(FR-010)**: Cập nhật tài liệu kỹ thuật trong `docs/ARCHITECTURE.md`, `docs/DESIGN-SYSTEM.md` và `docs/ROADMAP.md`.
