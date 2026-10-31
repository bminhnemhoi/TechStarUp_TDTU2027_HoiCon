---

description: "Tasks list — Spec 022 Sentinel v1 (HỏiCon Đợt 5 Làn A)"
---

# Tasks: Spec 022 — Lính gác v1 (Android)

**Input**: `specs/022-sentinel-v1/{spec.md, plan.md}`, `docs/schemas/risk_event.v1.json`, `data/bank_apps.vn.json`

**Chế độ chạy**: Tự hành một mạch (MASTER-PLAN §2.6).

**Phân làn sở hữu**: Làn A (Android) — `apps/android/**`. Không đụng `backend/**`.

---

## Phase 1: Room Database & Tink Encryption

- [x] T001 [A] Khởi tạo Room Database `SentinelDatabase.kt` với các Entity: `OutboxEventEntity`, `ThreatHashEntity`, `RiskWindowState` — FR-001 · Verify: `./gradlew -p apps/android :app:testDebugUnitTest`
- [x] T002 [A] Tích hợp bộ mã hóa Tink AEAD trong `TinkCryptoHelper.kt` để mã hóa/giải mã payload sự kiện trong Outbox — FR-001 · Verify: `./gradlew -p apps/android :app:testDebugUnitTest`

---

## Phase 2: Risk Window & Local Rules Engine

- [x] T003 [A] Hiện thực `PiiMasker.kt`: che số điện thoại (giữ 3 số cuối), tính `h1` theo SHA-256("hoicon:v1:" + e164), kiểm tra 0 rò rỉ số thô — FR-009, SC-005 · Verify: `./gradlew -p apps/android :app:testDebugUnitTest`
- [x] T004 [A] Hiện thực `RiskWindowManager.kt`: quản lý trạng thái mở/đóng cửa sổ rủi ro 600 giây sau cuộc gọi lạ — FR-003 · Verify: `./gradlew -p apps/android :app:testDebugUnitTest`
- [x] T005 [A] Hiện thực `LocalRulesEvaluator.kt`: đánh giá sự kiện tiền cảnh theo Luật R1 (app ngân hàng) và Luật R5 (app điều khiển từ xa — I1), tạo `RiskEvent` ghi vào Outbox — FR-004, SC-004 · Verify: `./gradlew -p apps/android :app:testDebugUnitTest`

---

## Phase 3: Outbox & Heartbeat Workers

- [x] T006 [A] Bổ sung phương thức `sendEvents(events)` và `sendHeartbeat(status)` trong `PairingApiClient.kt` gửi Bearer token thiết bị — FR-002, FR-008 · Verify: `./gradlew -p apps/android :app:testDebugUnitTest`
- [x] T007 [A] Hiện thực `OutboxWorker.kt`: tự động quét các sự kiện chưa gửi, giải mã Tink, gửi theo lô lên `POST /v1/events` khi có mạng — FR-002, SC-002 · Verify: `./gradlew -p apps/android :app:testDebugUnitTest`
- [x] T008 [A] Hiện thực `HeartbeatWorker.kt`: gửi định kỳ thông tin trạng thái quyền và phiên bản lên máy chủ — FR-008 · Verify: `./gradlew -p apps/android :app:testDebugUnitTest`

---

## Phase 4: UI Screens E6 & E7 (Compose)

- [x] T009 [A] Thiết kế màn hình E6 `ProtectionStatusScreen.kt` (Compose): trạng thái "Đang bảo vệ", thẻ liên hệ gia đình, nút "Hỏi con" cỡ $\ge 64$dp đạt WCAG AAA $\ge 7:1$ — FR-005, SC-003 · Verify: `./gradlew -p apps/android :app:compileDebugKotlin`
- [x] T010 [A] Thiết kế màn hình E7 `SafePauseScreen.kt` (Compose): đếm ngược an toàn 60 giây, câu nhắc "Hỏi người gọi mật khẩu gia đình" (I2), nút "Hủy giao dịch" & "Tôi muốn tiếp tục" — FR-006, SC-003, SC-004 · Verify: `./gradlew -p apps/android :app:compileDebugKotlin`
- [x] T011 [A] Tích hợp Android TTS tiếng Việt trong `SafePauseScreen.kt`: tự động phát cảnh báo giọng nói ngoại tuyến, nút "Nghe lại" $\ge 64$dp — FR-007, SC-001 · Verify: `./gradlew -p apps/android :app:assembleDebug`

---

## Phase 5: Verification & Quality Gates

- [x] T012 [A] Chụp ảnh kiểm chứng giao diện E6, E7 ở cỡ chữ 100% và 200% trên AVD `hc-api36` lưu vào `~/hoicon-evidence/022-sentinel-v1/shots/` — SC-003 · Verify: `ls ~/hoicon-evidence/022-sentinel-v1/shots/`
- [x] T013 [A] Cập nhật tài liệu kỹ thuật trong `docs/ARCHITECTURE.md`, `docs/DESIGN-SYSTEM.md` và `docs/ROADMAP.md` — FR-010 · Verify: review
- [x] T014 [A] Cổng chất lượng Làn A: Gradle build debug & release manifest check 0 quyền lạ ngoài khai báo; kiểm tra không có mã hex chép tay ngoài `Tokens.kt` — SC-003, SC-006 · Verify: `./gradlew -p apps/android :rules:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug`
