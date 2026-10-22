# Feature Specification: 037 — Gia cố phần còn lại (P2-20)

**Feature Branch**: `feat/037-hardening-rest` · **Created**: 23/10/2026 · **Status**: Draft (specify + clarify tự quyết, MASTER-PLAN §2.6)

**Input**: phần ngoài phạm vi của `specs/034-hardening-core` (§6 + "Medium chưa sửa" trong evidence 034) và MASTER-PLAN §3 Đợt 5
("Crashlytics, rà soát cuối; AC: crash-free đo được").

## Truy vết *(mandatory)*

- **Mã ROADMAP**: P2-20 (phần còn lại; lõi ở 034)
- **User story PRD**: không có story mới; bảo vệ US-01…US-07 trước M3
- **ADR liên quan**: ADR-005 (Play testing), ADR-006, ADR-010; không đổi quyết định nào
- **Gate nghiệm thu**: M3 (09/01/2027) — "0 Critical/High chưa xử lý", "crash-free đo được"
- **Phụ thuộc spec**: 034 (lõi), 011 (văn bản đồng ý, phiên bản đã duyệt), 012 (Play internal testing, VPS), 029 (thí điểm)
- **Làn**: A+B (A: `apps/android/**`; B: `backend/**`)

## Bối cảnh (chỉ phần chênh lệch)

Evidence 034 để lại 4 Medium + 5 Low có chủ đích "làm ở spec sau". Bốn Medium chạm đúng chỗ nhạy nhất của sản phẩm: đồng ý bị rút
mà tin vẫn đi (#4), app thử lại vô hạn khi đồng ý bị rút (#5), máy chủ nhận phiên bản văn bản không có trong danh sách (#7), sao
lưu cũ làm sống lại dữ liệu đã xóa (#6). Crashlytics trong kế hoạch ban đầu cần Firebase (W0-3, BLOCKED) **và** là luồng dữ liệu
mới gửi cho bên thứ ba (Google) ⇒ cần mục đích đồng ý + DPIA (luật 7) — phạm vi Minh.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Rút đồng ý là dừng ngay (Priority: P1)
Bác (hoặc người hướng dẫn) rút `guardian_alerts` giữa lúc sự cố đang mở ⇒ không tin Zalo nào đi nữa, kể cả nhắc T1/T2 và tin tổng
kết diễn tập; app nhận `403 consent_withdrawn` thì hiện đúng câu "đã ngừng báo cho con" và **không** thử lại.

**Independent Test**: pytest: sự cố mở → rút đồng ý → hẹn giờ T1 chạy ⇒ 0 dòng `messages_out` mới. Android unit test: 403 thân
`consent_withdrawn` ⇒ một trạng thái, 0 lần thử lại.

**Acceptance Scenarios**:
1. **Given** sự cố đang chờ người giám hộ, **When** rút `guardian_alerts` rồi T1 đến hạn, **Then** job `notify_guardian` kết thúc
   `skipped_consent`, không gọi Zalo, có `agent_steps`/log mã (không nội dung).
2. **Given** app gửi heartbeat, **When** máy chủ trả `403 {"error":"consent_withdrawn"}`, **Then** app dừng gửi kênh đó, E6 hiện
   trạng thái đúng, WorkManager không xếp lại.

### User Story 2 — Chỉ nhận văn bản đã có (Priority: P1)
`POST /v1/consents` với `consent_version`/`text_sha256` không có trong `docs/legal/consent/manifest.json` (bản đang phục vụ) ⇒ 422.

### User Story 3 — Đo được độ ổn định trước M3 (Priority: P2)
Đội thấy tỉ lệ không crash của bản internal testing **mà không thêm SDK** (Play Console Android vitals); Crashlytics chỉ thêm nếu
Minh duyệt mục đích dữ liệu mới.

### User Story 4 — Rà soát cuối (Priority: P2)
`privacy-audit` + `security-privacy-reviewer` toàn codebase trước đóng băng 06/01 ⇒ 0 Critical/High chưa xử lý.

### Edge Cases
- Rút rồi cấp lại đồng ý giữa T1 và T2 ⇒ T2 đi (kiểm lúc gửi, không đóng băng lúc mở sự cố).
- Tin Zalo của sự cố `sim`/`is_demo` không qua kiểm đồng ý thật (giữ hành vi 033/034).
- Khôi phục sao lưu mà sổ xóa trống ⇒ cảnh báo, không chặn khôi phục.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** `send_to_guardian` kiểm đồng ý `guardian_alerts` của người được bảo vệ **lúc gửi** (034 Medium #4): payload job mang
  `protected_member_id`; chưa/không còn đồng ý ⇒ trả `skipped_consent`, không chạm `messages_out`/Zalo. Áp cho mọi mẫu (sự cố, nhắc,
  leo thang, bằng chứng, hồ sơ 031, Coach 032, tổng kết diễn tập 028). Job cũ không có trường ⇒ tra theo `incident_id`.
- **FR-002** Thân `403` khi đồng ý bị rút thống nhất `{"error": "consent_withdrawn", "purpose": <enum>}` (hợp đồng
  `docs/schemas/error.v1.json` — thêm mã nếu chưa có) ở mọi route thiết bị.
- **FR-003** Android (034 Medium #5): nhận `consent_withdrawn` ⇒ trạng thái riêng (không gộp "cần ghép đôi lại"), dừng worker của
  mục đích đó, không thử lại; E6 hiện câu trong `strings.xml` (`ux-elder-reviewer`).
- **FR-004** (034 Medium #7) `POST /v1/consents`: `consent_version` + `text_sha256` phải khớp một dòng của `manifest.json` (nạp lúc
  khởi động); không khớp ⇒ 422 `unknown_consent_text`. Bản phát hành (`HOICON_ENV=prod`) chỉ nhận dòng `released`; dev/test nhận cả
  `draft`.
- **FR-005** (034 Low #9) Giới hạn tần suất `POST /v1/consents`: 30 lượt/giờ/thiết bị, 429 + `Retry-After`.
- **FR-006** (034 Medium #6, phối hợp 012) "Sổ xóa": mỗi lần `purge_family` ghi một dòng mã hóa (chỉ id gia đình + thời điểm) vào tệp
  ngoài DB cạnh bản sao lưu; `ops restore` chạy lại `purge_family` cho mọi id trong sổ sau khi khôi phục; có test khôi phục bản cũ ⇒
  dữ liệu đã xóa không sống lại.
- **FR-007** (034 Low #12, #14, #15) Nonce sao lưu dẫn xuất khóa phụ theo tệp (HKDF, thư viện `cryptography` đã có); `queue.py` bỏ
  `exc_info` có thể kèm tham số SQL (log tên lớp lỗi); fixture `0912345678` đổi sang dải hư cấu `0900000xxx`.
- **FR-008** Đo ổn định không thêm SDK: tài liệu `docs/setup/STABILITY.md` (đọc Android vitals của Play Console: crash/ANR theo phiên
  bản, ngưỡng "bad behavior" của Play) + mục trong `ops pilot report` ghi số đọc tay. **Crashlytics: chỉ khi Minh duyệt** mục đích
  dữ liệu mới (MASTER-PLAN §8 mục 13); khi đó thêm giá trị enum đồng ý + văn bản (luật 7), bật thu thập chỉ sau đồng ý.
- **FR-009** Rà soát cuối: `privacy-audit` + `security-privacy-reviewer` (toàn codebase, ma trận IDOR mọi route `{id}`) + quét
  `gitleaks`/`osv-scanner`; mọi Critical/High sửa trong spec này, Medium ghi quyết định.

### Key Entities
- Sổ xóa (tệp, không phải bảng): `{family_id, purged_at}` mã hóa bằng khóa sao lưu.

## Bất biến an toàn *(mandatory)*
Không đụng đường dừng an toàn và luật trên máy. Kiểm đồng ý lúc gửi **không** được chặn câu nhắc trên máy của bác (E7 vẫn hiện khi
rút `guardian_alerts` — chỉ thôi báo con, đúng câu trong văn bản đồng ý).

## Quyền riêng tư & đồng ý *(mandatory)*
FR-001/003/004 làm đúng lời hứa của văn bản `guardian_alerts` ("chỉ không báo con nữa"). Không mục đích mới trừ Crashlytics (chờ Minh).
Sổ xóa chỉ chứa id gia đình (giả danh), mã hóa.

## UX người cao tuổi
Một câu mới ở E6 (FR-003): `ux-elder-reviewer` đọc ở 100% + 200%.

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: Rút đồng ý ⇒ 0 tin Zalo mới trên 7 loại mẫu (pytest, mỗi loại ≥ 1 ca).
- **SC-002**: App: 403 `consent_withdrawn` ⇒ 0 lần thử lại trong 24 giờ giả lập (unit test WorkManager).
- **SC-003**: `POST /v1/consents` văn bản lạ ⇒ 422; 31 lượt/giờ ⇒ 429 (pytest).
- **SC-004**: Khôi phục bản sao lưu cũ + sổ xóa ⇒ 0 dòng của gia đình đã xóa (pytest với DB tạm).
- **SC-005**: Rà soát cuối 0 Critical/High chưa xử lý (báo cáo reviewer).
- **SC-006**: Tỉ lệ phiên không crash đọc được từ Android vitals cho bản internal testing — **BLOCKED** tới khi có Play Console (W0-3)
  và người cài thật.

## Kế hoạch bằng chứng *(mandatory)*
`evidence.md` theo mẫu: SC-001…005 có số + môi trường; SC-006 BLOCKED có lý do; báo cáo reviewer; lệnh cổng.

## Ngoài phạm vi & mốc cắt
Màn E12 xóa dữ liệu trên app, xuất dữ liệu, `/v1/auth/refresh` + xoay khóa JWT (ghi ROADMAP "Ghi chú"). Cắt khi trễ: FR-005 rồi FR-007.
**Không bao giờ cắt**: FR-001, FR-003, FR-004 (sổ đồng ý, che PII).

## Assumptions
Gia đình thí điểm < 50 ⇒ nạp manifest vào bộ nhớ đủ. Play Console có Android vitals cho internal testing khi có ≥ vài người cài.
