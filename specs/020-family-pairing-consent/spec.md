# Feature Specification: Spec 020 — Ghép đôi gia đình & Sổ đồng ý bất biến (Family Pairing & Consent Ledger)

**Feature Branch**: `feat/020-pairing-consent-android` (Làn A) · `feat/020-pairing-consent-server` (Làn B)

**Created**: 2026-10-15

**Status**: Ready — Soạn theo ủy quyền của Tổng tư lệnh Tiến (15/10/2026), khởi động Đợt 4 và lát dọc MVP Phase 2 theo chế độ tự hành một mạch (MASTER-PLAN §2.6, §5 luật 7).

## 1. Truy vết *(mandatory)*

- **Mã ROADMAP**:
  - **P2-01**: DB v1 + migration (`devices`, `consents` trigger chỉ ghi thêm, `trusted_contacts`, `action_tokens`).
  - **P2-02**: Ghép đôi, xác thực thiết bị, API đồng ý; luồng màn hình E1–E4 trên Android.
- **User stories PRD**:
  - **US-01**: Ghép đôi thiết bị trong < 5 phút; mã 6 số hết hạn sau 15 phút; hiển thị tên gia đình sau khi kết nối.
  - **US-04**: Minh bạch quyền riêng tư; sổ đồng ý bất biến (Consent Ledger append-only, chống chối bỏ).
- **ADR & Chính sách liên quan**:
  - `ADR-006`: Băm số điện thoại / PII, không lưu số thô.
  - `ADR-010`: Kiến trúc định danh gia đình & phân quyền qua Zalo/App.
  - `docs/PLAY-POLICY.md`: Yêu cầu bắt buộc về **Công bố nổi bật (Prominent Disclosure)** trước khi gọi API xin quyền nhạy cảm (Accessibility, UsageStats, Call screening).
  - `docs/PRIVACY-DPIA.md`: Lưu vết đồng ý có phiên bản và chữ ký băm nội dung (`text_sha256`).
- **Phụ thuộc spec**:
  - `specs/010-design-system`: Bắt buộc dùng `tokens.json` v1.0.0 và font Be Vietnam Pro cho màn E1–E4.
  - `specs/002-zalo-guardian-channel`: Dùng lại bảng `families`, `members`, `pairing_codes` từ migration 0003.
  - `specs/003-agent-core-mcp-threat`: Dùng lại cấu trúc HMAC nhiều kid và pepper.
- **Làn phân công**:
  - **Làn A (Android)**: `apps/android/**` — Các màn hình E1 (Chào mừng), E2 (Nhập mã 6 số), E3 (Công bố nổi bật Prominent Disclosure), E4 (Cấp quyền hệ thống & gửi đồng ý), ViewModel, Token Storage.
  - **Làn B (Server)**: `backend/**`, `docs/schemas/**` — Migration `0005`, Trigger Postgres chống sửa/xóa `consents`, API `POST /v1/pair`, API `POST /v1/consents`, JWT Auth thiết bị.

---

## 2. User Scenarios & Testing *(mandatory)*

### User Story 1 - Người cao tuổi nhập mã 6 số từ con để ghép đôi máy bảo vệ (Priority: P1) 🎯 MVP

Con tạo mã ghép đôi trên bot Zalo (đã có từ spec 002). Cha/mẹ mở ứng dụng HỏiCon lần đầu, thấy màn E1 giới thiệu ấm áp, bấm "Bắt đầu", sang màn E2 nhập 6 chữ số to rõ. Ứng dụng gọi `POST /v1/pair`. Máy chủ xác thực mã, liên kết thiết bị vào gia đình, trả về định danh và token. Ứng dụng hiển thị câu chào: "Đã kết nối với [Tên gia đình]".

**Acceptance Scenarios**:
1. **Given** mã 6 số hợp lệ chưa dùng và còn hạn 15 phút trong `pairing_codes`, **When** thiết bị gửi `POST /v1/pair` với `code`, **Then** máy chủ trả 200 kèm JWT thiết bị, đánh dấu mã `used_at = now()`, tạo dòng trong `devices`.
2. **Given** mã đã hết hạn hoặc đã dùng hoặc không tồn tại, **When** gửi `POST /v1/pair`, **Then** máy chủ trả 400 Bad Request kèm thông báo lỗi tiếng Việt thân thiện, không tiết lộ thông tin nội bộ.
3. **Given** nhập mã thành công trên Android, **When** nhận phản hồi 200, **Then** lưu JWT an toàn vào bộ nhớ mã hóa và chuyển sang màn E3.

---

### User Story 2 - Sổ đồng ý bất biến (Consent Ledger) bảo vệ quyền riêng tư (Priority: P1)

Mọi sự đồng ý của cha mẹ (hoặc người giám hộ) được ghi vào bảng `consents` kèm phiên bản chính sách và mã băm toàn văn. Bảng này tuyệt đối KHÔNG cho phép sửa (`UPDATE`) hoặc xóa (`DELETE`), kể cả quản trị viên máy chủ — chỉ được phép ghi thêm dòng mới (`granted=false` khi rút quyền) theo đúng Nghị định 356/2025 và Luật Bảo vệ dữ liệu cá nhân.

**Acceptance Scenarios**:
1. **Given** thiết bị đã ghép đôi gửi `POST /v1/consents` kèm danh sách mục đồng ý, **When** xác thực JWT hợp lệ, **Then** chèn các dòng mới vào `consents` với `recorded_at = now()`.
2. **Given** có ai đó (hoặc bug phần mềm) chạy lệnh `UPDATE consents SET ...` hoặc `DELETE FROM consents WHERE ...`, **Then** Postgres Trigger `prevent_consent_tamper` lập tức hủy giao dịch và ném lỗi `EXCEPTION`.

---

### User Story 3 - Công bố nổi bật (Prominent Disclosure) trước khi xin quyền Android (Priority: P1)

Trước khi hệ thống Android hiện bất kỳ hộp thoại xin quyền nhạy cảm nào (Trợ năng / UsageStats / Thông báo), ứng dụng PHẢI hiển thị màn E3 giải thích rõ ràng bằng tiếng Việt: Dữ liệu gì được thu thập, dùng làm gì (chỉ phát hiện lừa đảo trong cuộc gọi lạ), cam kết không ghi âm cuộc gọi và không bán dữ liệu. Người dùng bấm "Tôi đồng ý" mới kích hoạt hộp thoại hệ thống ở màn E4.

**Acceptance Scenarios**:
1. **Given** người dùng ở màn E2 ghép đôi xong, **When** chuyển tiếp, **Then** màn E3 hiện ra toàn màn hình, nêu rõ 4 mục công bố theo `docs/PLAY-POLICY.md`.
2. **Given** người dùng bấm "Xem chi tiết", **When** cuộn trang, **Then** chữ to $\ge 20$sp, độ tương phản $\ge 7:1$, Be Vietnam Pro hiển thị sắc nét.

---

## 3. Yêu cầu chức năng (FR)

- **FR-001**: Migration `0005_device_pairing_consent.py` tạo các bảng: `devices`, `consents`, `trusted_contacts`, `action_tokens` theo đúng `docs/DATA-MODEL.md`.
- **FR-002**: Tạo PostgreSQL Trigger `prevent_consent_tamper` trên bảng `consents` chặn mọi hành vi `UPDATE` hoặc `DELETE`.
- **FR-003**: Hiện thực API `POST /v1/pair` tuân thủ `docs/schemas/pair_request.v1.json` và `docs/schemas/pair_response.v1.json`.
- **FR-004**: Cơ chế JWT thiết bị (`DeviceAuth`): payload chứa `device_id`, `family_id`, `member_id`, thời hạn sống token 30 ngày, refresh token hỗ trợ gia hạn.
- **FR-005**: Hiện thực API `POST /v1/consents` tuân thủ `docs/schemas/consent_record.v1.json`, yêu cầu xác thực JWT thiết bị.
- **FR-006**: Android Màn E1 (`WelcomeScreen.kt`): Giao diện chào mừng, đồ họa tối giản, thông điệp gia đình ấm áp.
- **FR-007**: Android Màn E2 (`PairingScreen.kt`): Ô nhập 6 số lớn, tự động nhảy số hoặc bàn phím số chuyên dụng, nút bấm $\ge 64$dp.
- **FR-008**: Android Màn E3 (`ProminentDisclosureScreen.kt`): Tuân thủ chính sách Google Play 2026 về Accessibility & Sensitive Permissions.
- **FR-009**: Android Màn E4 (`PermissionsScreen.kt`): Kích hoạt các Intent xin quyền hệ thống tương ứng (Accessibility, UsageStats, Notifications) và gửi trạng thái lên `POST /v1/consents`.
- **FR-010**: Áp dụng 100% token màu từ `Tokens.kt` và font `res/font/be_vietnam_pro_*.ttf` từ spec 010. Không hardcode màu hex hay font hệ thống.
- **FR-011**: Tuyệt đối không ghi nhận số điện thoại thô hay tên thật không mã hóa.
- **FR-012**: Kiểm thử hợp đồng JSON Schema với bộ fixture valid/invalid cho cả 3 schema.
- **FR-013**: Cập nhật `docs/DATA-MODEL.md`, `docs/API.md`, và đánh dấu tiến độ trong `docs/ROADMAP.md` (P2-01, P2-02 sang `◐`).

---

## 4. Tiêu chí thành công (SC)

| Mã | Tiêu chí | Ngưỡng đo | Phương pháp kiểm chứng |
|---|---|---|---|
| **SC-001** | Thời gian ghép đôi thành công | < 5 phút; mã hết hạn 15' bị chặn | Test tự động integration API và kịch bản người dùng |
| **SC-002** | Bất biến của Sổ đồng ý | 100% lệnh UPDATE/DELETE trên `consents` bị Postgres Trigger chặn đứng | Test integration SQLAlchemy chạy `UPDATE` và `DELETE` bắt exception |
| **SC-003** | Tuân thủ chính sách Google Play | E3 Prominent Disclosure luôn xuất hiện trước khi gọi requestPermission | Kiểm tra luồng UI Compose State & Activity Lifecycle |
| **SC-004** | Tương phản & Khả năng đọc | 100% cặp text/nền $\ge 7.0:1$, chữ $\ge 20$sp cho người cao tuổi | Unittest tokens.json & UX elder reviewer |
| **SC-005** | Bảo vệ PII | 0 số điện thoại thô, 0 plain-text PII trong DB và network log | `privacy-audit` & grep byte DB |
| **SC-006** | Hồi quy & Ổn định | Toàn bộ test suite backend (pytest $\ge 615$) và Android Gradle build xanh | CI GitHub Actions |
