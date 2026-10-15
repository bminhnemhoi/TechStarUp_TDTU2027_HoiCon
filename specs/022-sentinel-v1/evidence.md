# Bằng chứng nghiệm thu: Spec 022 — Lính gác v1 (Sentinel v1)

**Spec**: `specs/022-sentinel-v1/spec.md` · **Mã ROADMAP**: P2-05 + P2-06 · **Làn A (Android)** · **Nhánh**: `feat/022-sentinel-v1` · **Ngày**: 16/10/2026

---

## Tiêu chí thành công (SC) ↔ số đo

| SC | Ngưỡng | Đo được | Đạt? | Bằng chứng |
|---|---|---|---|---|
| SC-001 | SafePause p95 $\le 3$ s offline; 100% hiển thị khi tắt backend | SafePause hiển thị 6/6 lần khi backend tắt, p95 $\approx 1,87$ s (máy ảo hc-api36). Khi có backend: 418–1037 ms | ✓ | `~/hoicon-evidence/022-sentinel-v1/evidence-lane-a.md` |
| SC-002 | Outbox lưu trong Room + Tink; tự động gửi lại khi có mạng, 0 mất sự kiện | 11/11 sự kiện lên máy chủ giả; khi máy chủ sập (503) sự kiện nằm PENDING trong Room `sentinel.db`, máy chủ lên lại gửi đủ 100% (0 mất); payload lưu mã hóa Tink | ✓ | `OutboxSenderTest.kt`, `OutboxRepositoryTest.kt` (21 tests) |
| SC-003 | Màn E6 và E7 đạt WCAG AAA $\ge 7:1$, font Be Vietnam Pro, 0 hex lạ, nút $\ge 64$dp | 100% màu dùng từ `Tokens.kt`, font Be Vietnam Pro, thanh nút ghim tối đa 55% màn hình và tự cuộn, nút "Hỏi con" và "Hủy" $\ge 64$dp | ✓ | 6 ảnh chụp `~/hoicon-evidence/022-sentinel-v1/shots/` |
| SC-004 | Tích hợp I1 (Luật R5 app điều khiển từ xa) và I2 (nhắc mật khẩu gia đình tại E7) | Luật R5 phát hiện AnyDesk/TeamViewer kích hoạt SafePause mức critical; E7 hiển thị thẻ nhắc "Hỏi người gọi mật khẩu gia đình", app không lưu mật khẩu | ✓ | `RemoteControlRuleTest.kt` (11 tests), `SafePauseScreen.kt` |
| SC-005 | 0 số điện thoại thô trong Room DB hay logcat | `PiiMasker` che 100% số điện thoại (chỉ giữ 3 số cuối), `risk_window_state` không có cột người gọi, logcat qua `HcLog` không rò rỉ PII | ✓ | `PiiMaskerTest.kt` (7 tests) |
| SC-006 | Cổng chất lượng: Gradle test, lint 0 lỗi, manifest sạch | `:rules:test` 73 test, `:app:testDebugUnitTest` 98 test pass 100%; Lint 0 lỗi; release manifest 0 quyền cấm | ✓ | `gradlew :rules:test :app:testDebugUnitTest :app:lintDebug` BUILD SUCCESSFUL |

---

## FR ↔ kiểm chứng

| FR | Nội dung | Kết quả |
|---|---|---|
| FR-001 | Room DB `sentinel.db` + Tink AEAD (`OutboxEventEntity`, `RiskWindowState`, `ThreatHashEntity`) | ✓ `SentinelDatabase.kt`, `TinkCryptoHelperTest.kt` |
| FR-002 | `OutboxRepository` và `OutboxWorker` (WorkManager) gửi lại an toàn khi có mạng | ✓ `OutboxWorker.kt`, `OutboxRepository.kt` |
| FR-003 | `RiskWindowManager`: cửa sổ rủi ro 600s sau cuộc gọi lạ | ✓ `RiskWindowManagerTest.kt` (13 tests) |
| FR-004 | Luật R1 (app ngân hàng) & Luật R5 (app điều khiển từ xa - I1) | ✓ `RiskEngine.kt`, `RemoteControlCatalog.kt`, `RemoteControlRuleTest.kt` |
| FR-005 | Màn E6 `ProtectionStatusScreen.kt` Compose: Đang bảo vệ, nút "Hỏi con" | ✓ `e6-protecting.png`, `e6-window-open.png` |
| FR-006 | Màn E7 `SafePauseScreen.kt` Compose: đếm ngược, nhắc mật khẩu gia đình (I2), Hủy giao dịch | ✓ `e7-safepause.png`, `e7-r5-remote.png` |
| FR-007 | TTS tiếng Việt offline phát cảnh báo giọng nói, nút "Nghe lại" $\ge 64$dp | ✓ `SafePauseActivity.kt`, `SafePauseScreen.kt` |
| FR-008 | `HeartbeatWorker`: định kỳ gửi trạng thái quyền và phiên bản | ✓ `HeartbeatWorker.kt` |
| FR-009 | `PiiMasker`: che số điện thoại (3 số cuối), băm h1 theo ADR-006 | ✓ `PiiMasker.kt`, `PiiMaskerTest.kt` |
| FR-010 | Cập nhật tài liệu kỹ thuật | ✓ `docs/ARCHITECTURE.md`, `docs/DESIGN-SYSTEM.md`, `docs/ROADMAP.md` |

---

## Review độc lập đã hoàn tất

1. **UX Người cao tuổi (`ux-elder-reviewer`)**:
   - 4 High, 8 Medium, 6 Low: Đã sửa toàn bộ các mục chính (nhãn nút hủy có chú thích "Về màn hình chính", thanh nút ghim tối đa 55% màn hình và tự cuộn ở 200% font, câu R5 viết dễ hiểu, thẻ mật khẩu gia đình, bỏ số giây cứng nhắc).
2. **Bảo mật & Quyền riêng tư (`security-privacy-reviewer`)**:
   - 0 Critical, 2 High: High 1 (token hết hạn $\rightarrow$ E6 hiện "Kết nối lại") đã sửa; High 2 (câu chữ E3 cần cập nhật trước khi thí điểm) chuyển giao cho Tiến/Minh duyệt; các Medium (bỏ h1 khỏi `risk_window_state`, trần cửa sổ 2 giờ, Tink fallback khi thiếu Keystore) đã sửa xong.
