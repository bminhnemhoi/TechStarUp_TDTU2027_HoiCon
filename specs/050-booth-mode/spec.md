# Feature Specification: 050 — Chế độ gian trưng bày (P4-02)

**Feature Branch**: `feat/050-booth-mode` · **Created**: 23/10/2026 · **Status**: Draft (specify + clarify tự quyết, MASTER-PLAN §2.6)

**Input**: ROADMAP P4-02 + Gate G4; MASTER-PLAN §3 Đợt 6 (`/booth`, `/join/[code]`, `/demo/console`, phát lại khi mất mạng,
reset demo < 1 phút). Thời điểm thi công: **sau nộp Vòng 2 (09/01/2027)**, xong trước 07/02/2027.

## Truy vết *(mandatory)*

- **Mã ROADMAP**: P4-02 · **Gate**: G4 (26/02/2027): chạy gian 3 lần liên tiếp thành công, cảnh báo < 5 s, phát lại khi mất mạng,
  video dự phòng, reset demo < 1 phút
- **User story PRD**: US-10 (BGK thử toàn luồng) mở rộng cho khách tham quan gian
- **ADR liên quan**: ADR-002, ADR-003/010 (Zalo — gian **không** gửi Zalo thật cho khách), ADR-012
- **Phụ thuộc spec**: 033 (`/sim`, `/trace`, cờ `sim`, thiết bị demo riêng mỗi lượt), 012 (bản `demo` Android, VPS), 028 (nhãn diễn tập)
- **Làn**: A+B

## Bối cảnh (chỉ phần chênh lệch)

033 đã có điện thoại mô phỏng trên web cho một người xem. Ở gian chung kết (bình chọn tại gian = 30% điểm), cần: một màn lớn
cho đám đông (`/booth`), khách quét QR để **xem trên điện thoại của mình** tin cảnh báo như người giám hộ (`/join/[code]`, không
Zalo, không thu số điện thoại), một bàn điều khiển cho đội (`/demo/console`: chọn kịch bản, chạy trên máy Android `demo` thật hoặc
mô phỏng, reset), và đường dự phòng khi mạng gian chập chờn.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Đội chạy một lượt demo từ bàn điều khiển (Priority: P1)
Thành viên đội chọn kịch bản trên `/demo/console`, bấm "Chạy" ⇒ máy Android `demo` (hoặc điện thoại mô phỏng) hiện E7, màn `/booth`
hiện từng bước tác tử, khách đã quét QR thấy tin cảnh báo trên điện thoại mình **< 5 s** sau sự kiện.

**Independent Test**: Playwright 3 trình duyệt (console, booth, join) trên API dev + `HOICON_BOOTH_ENABLED=true`, replay.

**Acceptance Scenarios**:
1. **Given** gian bật, 1 khách đã vào `/join/<mã>`, **When** console chạy `fake_police_safe_account_002`, **Then** khách thấy tin mở
   đầu "Đây là trợ lý AI HỏiCon" + nhãn "MÔ PHỎNG" trong < 5 s; `/booth` hiện sơ đồ + bản chữ.
2. **Given** lượt đang chạy, **When** console bấm "Làm lại", **Then** < 1 phút mọi màn về trạng thái đầu, không còn sự cố/thiết bị
   `sim:` của lượt trước.

### User Story 2 — Khách tham quan tự xem (Priority: P1)
Khách quét QR trên màn `/booth` ⇒ `/join/<mã>` (mã đổi mỗi lượt, hết hạn 15 phút), không đăng nhập, không nhập số điện thoại, không
cookie theo dõi; thấy đúng tin người giám hộ sẽ nhận và nút "nghi lừa đảo / an toàn" (chỉ ghi phiếu bình chọn ẩn danh nếu có, không
đổi sự cố).

### User Story 3 — Mất mạng vẫn demo được (Priority: P1)
Mạng gian rớt ⇒ console chuyển "phát lại cục bộ": `/booth` chạy bản ghi sẵn của lượt replay (tệp tĩnh trong web), E7 trên máy Android
vẫn hiện (không cần mạng — luật 4); `/join` hiện "Mạng đang chập chờn, mời bác/anh/chị xem trên màn lớn".

### Edge Cases
- > 50 khách cùng vào ⇒ SSE fan-out không làm chậm `/booth` (đo).
- Mã QR cũ (lượt trước) ⇒ "Lượt này đã xong, mời quét mã mới".
- Gian không được chạm gia đình thật: cổng `HOICON_BOOTH_ENABLED` + chỉ gia đình demo (như 033 FR-002/003).

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001** Hợp đồng trước: `booth_session.v1.json` (mã tham gia, hạn, trạng thái lượt, `run_id`), `booth_event.v1.json` (sự kiện
  SSE cho khách: tin người giám hộ đã che PII, bước tóm tắt) + fixture.
- **FR-002** Cổng `HOICON_BOOTH_ENABLED` (mặc định tắt, `compose.prod.yml` không đặt); mọi route `/v1/booth/*` 404 khi tắt; console cần
  phiên demo (như `/v1/sim/*`).
- **FR-003** `POST /v1/booth/sessions` (console) tạo lượt = một lượt `/v1/sim/runs` (033) + mã tham gia 6 ký tự (không ký tự dễ nhầm),
  hạn 15 phút; `POST /v1/booth/sessions/{id}/reset` xóa sự cố/thiết bị `sim:` của lượt (< 1 phút, đo).
- **FR-004** `GET /v1/booth/join/{code}/stream` (SSE, không đăng nhập): chỉ phát `booth_event` của đúng lượt; giới hạn 200 kết nối/lượt,
  30 lần mở/phút/IP (IP không lưu quá bộ nhớ đệm giới hạn tần suất).
- **FR-005** Lượt gian có thể dùng **máy Android `demo` thật**: console hiện mã ghép đôi của gia đình demo; sự kiện của máy đó đi đường
  `/v1/events` thường, sự cố mang `sim` nhờ thiết bị thuộc gia đình demo đã gắn "chế độ gian" (không gửi Zalo thật — như 033 D10).
- **FR-006** Web: `/booth` (màn lớn 1920×1080, chữ ≥ 32 px, QR, sơ đồ + bản chữ, nhãn "MÔ PHỎNG" token `sim.*`), `/join/[code]` (điện
  thoại, chữ ≥ 18 px, nút ≥ 44 px), `/demo/console` (chọn kịch bản theo `title_vi`, chạy, làm lại, chuyển phát lại cục bộ).
- **FR-007** Phát lại cục bộ: `apps/web/public/booth/replay/<kịch bản>.json` sinh từ một lượt replay thật (`scripts/booth-record.py`),
  không chứa PII; `/booth` chạy được khi API không trả lời.
- **FR-008** Tài liệu `docs/setup/BOOTH.md` (bật gian, chuẩn bị máy `demo`, quy trình reset, dự phòng video) + kịch bản tổng duyệt G4.

### Key Entities
- `booth_sessions` (bảng mới, làn B tạo migration): `id`, `code`, `run_id`, `expires_at`, `state`; xóa sau 24 giờ.

## Bất biến an toàn *(mandatory)*
Không đổi đường dừng an toàn; máy `demo` vẫn hiện E7 offline. Không tin Zalo thật nào từ lượt gian. Công khai AI ở mọi tin khách thấy.

## Quyền riêng tư & đồng ý *(mandatory)*
Khách không cung cấp dữ liệu cá nhân nào; không cookie theo dõi; dữ liệu demo hư cấu, `is_demo`. IP chỉ dùng cho giới hạn tần suất
trong bộ nhớ. Không mục đích đồng ý mới.

## UX người cao tuổi
`/join` có thể do người cao tuổi đến gian mở: chữ ≥ 18 px, tương phản ≥ 7:1, câu ấm áp; `ux-elder-reviewer` đọc ảnh.

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: Tin tới `/join` < 5 s sau sự kiện (p95, 20 lượt, mạng LAN gian giả lập).
- **SC-002**: Reset < 1 phút (n = 10).
- **SC-003**: 3 lượt liên tiếp không lỗi trên máy Android `demo` thật (Gate G4) — **BLOCKED** tới khi có máy thật.
- **SC-004**: Ngắt API ⇒ `/booth` phát lại cục bộ đủ bước (Playwright, chặn mạng).
- **SC-005**: 0 PII trong `booth_event` và DOM ba trang; cổng tắt ⇒ 404 (pytest + Playwright).
- **SC-006**: 100 kết nối SSE đồng thời ⇒ `/booth` vẫn nhận bước < 1 s (đo trên máy dev).

## Kế hoạch bằng chứng *(mandatory)*
`evidence.md`: SC-001…006 (SC-003 BLOCKED nếu chưa có máy thật), ảnh 1920/390, báo cáo `ux-elder-reviewer` + `security-privacy-reviewer`.

## Ngoài phạm vi & mốc cắt
Bình chọn trong app (BTC tự tổ chức). Cắt khi trễ (theo thứ tự): FR-005 (máy thật ⇒ chỉ mô phỏng), US-2 nút trả lời của khách.
**Không cắt**: FR-002, FR-007 (dự phòng mất mạng), công khai AI.

## Assumptions
Mạng gian là Wi-Fi BTC hoặc điểm phát của đội; ≤ 200 khách/lượt; một màn lớn HDMI.
