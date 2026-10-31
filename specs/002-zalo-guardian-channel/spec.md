# Feature Specification: Kênh Zalo cho người giám hộ (spike P1-S3)

**Feature Branch**: `feat/002-zalo-guardian-channel`

**Created**: 2026-10-15

**Status**: Draft

**Input**: User description: "Spec 002 (docs/MASTER-PLAN.md §3, Đợt 1, làn B): P1-S3 — webhook Zalo Bot
`POST /webhooks/zalo/{bot_id}` (kiểm secret, chống trùng, trả 200 ngay, xử lý trong job), `/start <mã>` ghép người giám
hộ, nút/trả lời Đã gọi – Lừa đảo – An toàn, `notify_guardian` gửi thật qua bộ đếm hạn mức `messages_out`, chế độ MOCK cho
test/CI khi chưa có token, đo giao tin p95 ≤ 5 s, ADR-010, chốt kênh dự phòng. Dùng lại `jobs/queue.py`, `agents/texts.py`."

<!--
  HỎICON (brownfield): nền tảng Zalo đã chọn ở ADR-003 (kèm yêu cầu bảo mật bắt buộc). Đồ thị sự cố, hẹn giờ T1/T2/T3,
  job `notify_guardian` đã có từ P1-S4 (ADR-009) nhưng chưa gửi thật. ADR-010 là SẢN PHẨM của spec này (chưa tồn tại).
-->

## Truy vết *(mandatory)*

- **Mã ROADMAP**: P1-S3 (Zalo Bot: webhook qua cloudflared, `/start <mã>`, nút bấm, đo hạn mức thật, điều khoản)
- **User story PRD**: US-03 (con nhận cảnh báo Zalo ≤ 10 s và bấm được hành động), một phần US-01 (ghép Zalo của con)
- **ADR liên quan**: ADR-003 (Zalo Bot Platform + yêu cầu bảo mật), ADR-006 (HMAC), ADR-009 (job, `notify_guardian`,
  `fast_alert` không LLM). **ADR-010 (mới)**: kết quả spike + hai đề xuất D1, D2 dưới đây — **Minh duyệt**.
- **Gate nghiệm thu**: G1 (08/11) — báo cáo spike có số đo + ADR-010; tiền đề M1 ("Zalo giai đoạn 1 p95 ≤ 10 s")
- **Phụ thuộc spec**: không. Phụ thuộc ngoài: **token bot dev Zalo (W0-3, Minh)** cho phần gửi thật và số đo.
- **Làn**: B (backend). Không đụng `apps/android/**`.

### Đề xuất cần Minh duyệt trước khi viết migration (ghi ở ADR-010)
- **D1 — Lưu định danh Zalo:** muốn *gửi* tin cần `chat_id` thật, nhưng DATA-MODEL ghi `members.zalo_user_ref (HMAC)`
  (không đảo ngược được) và luật 1 cấm lưu Zalo ID thô. Đề xuất: lưu **`chat_id` mã hóa** (AES-GCM, khóa riêng có `kid`,
  giống cách pepper) để gửi + **HMAC** để tra cứu/chống trùng; không bao giờ log/in. Phương án khác: lưu thô (vi phạm
  luật 1 — loại), chỉ HMAC (không gửi được — loại).
- **D2 — Bảng ghép đôi:** `/start <mã>` cần `families`, `members`, `pairing_codes`, và tin đi cần `messages_out`. Đề xuất:
  spec này tạo migration cho **đúng 4 bảng đó theo DATA-MODEL** (cột Zalo theo D1); spec 020 thêm phần còn lại
  (devices, consents, trusted_contacts, action_tokens) và luồng ghép đôi từ app. Phương án khác: bảng tạm cho spike
  (rác trong migration bất biến — loại); hoãn `/start` sang 020 (spike không đo được đầu–cuối — dự phòng nếu Minh từ chối).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Con nhận cảnh báo Zalo ngay khi có sự cố (Priority: P1)

Khi Lính gác báo sự cố, người giám hộ đã ghép đôi nhận tin Zalo mẫu (không cần AI) trong vài giây, mở đầu bằng câu công
khai AI, kèm cách phản hồi.

**Why this priority**: Đây là "đường cảnh báo" — một mục không bao giờ cắt — và là lý do người giám hộ trả tiền.

**Independent Test**: Ở chế độ mock: mở một sự cố demo ⇒ kiểm tin đã "gửi" đúng nội dung, đúng người nhận, có dòng
`messages_out`. Ở chế độ thật (khi có token): đo thời gian từ lúc xếp tin tới lúc Zalo xác nhận, n ≥ 20.

**Acceptance Scenarios**:

1. **Given** một gia đình có người giám hộ hạng 1 đã ghép Zalo, **When** sự cố mở và `fast_alert` xếp tin,
   **Then** tin được gửi một lần duy nhất, mở đầu "Đây là trợ lý AI HỏiCon.", và một dòng `messages_out` ghi trạng thái.
2. **Given** sự cố là diễn tập, **When** tin được gửi, **Then** tin có nhãn `[DIỄN TẬP]` ngay sau câu công khai.
3. **Given** Zalo trả lỗi tạm thời, **When** job gửi chạy lại, **Then** tin không bị gửi hai lần cho cùng một lần xếp.

---

### User Story 2 - Con ghép Zalo với gia đình bằng mã (Priority: P1)

Người giám hộ nhắn `/start <mã 6 số>` cho bot; HỏiCon gắn Zalo đó vào đúng gia đình và trả lời xác nhận.

**Why this priority**: Không ghép thì không có người nhận cho US1.

**Independent Test**: Tạo mã bằng lệnh vận hành (luồng tạo mã từ app thuộc spec 020) ⇒ gửi cập nhật `/start <mã>` giả
lập ⇒ kiểm người giám hộ được gắn, mã không dùng lại được.

**Acceptance Scenarios**:

1. **Given** mã còn hạn, **When** nhắn `/start <mã>`, **Then** người giám hộ được gắn vào gia đình, bot trả lời xác nhận
   (mở đầu bằng câu công khai AI), mã bị đánh dấu đã dùng.
2. **Given** mã sai, hết hạn (> 15 phút) hoặc đã dùng, **When** nhắn `/start <mã>`, **Then** bot trả lời hướng dẫn chung,
   không tiết lộ mã đó có tồn tại hay không.
3. **Given** cùng một Zalo nhắn `/start` lần hai cho cùng gia đình, **Then** không tạo người giám hộ trùng.

---

### User Story 3 - Con phản hồi bằng nút hoặc trả lời 1/2/3 (Priority: P2)

Người giám hộ bấm nút (nếu nền tảng hỗ trợ) hoặc trả lời "1" (đã liên lạc – an toàn), "2" (nghi lừa đảo), "3" (xem chi
tiết);
HỏiCon ghi nhận và đồ thị sự cố đang chờ người giám hộ chạy tiếp.

**Why this priority**: Hoàn tất vòng "báo – phản hồi"; phần đóng sự cố đầy đủ và trang hành động thuộc spec 023.

**Independent Test**: Gửi cập nhật giả lập "1" sau một tin cảnh báo ⇒ đồ thị ở trạng thái chờ người giám hộ được resume
với quyết định tương ứng.

**Acceptance Scenarios**:

1. **Given** sự cố đang chờ người giám hộ, **When** người giám hộ trả lời "1", **Then** đồ thị nhận quyết định "an toàn"
   và bot xác nhận đã nhận; trả lời "3" chỉ gửi chi tiết, không đổi trạng thái chờ.
2. **Given** Zalo gửi lại cùng một cập nhật nhiều lần, **When** webhook nhận, **Then** chỉ xử lý một lần.
3. **Given** nội dung trả lời không hiểu được, **Then** bot hướng dẫn lại 1/2/3, không thay đổi sự cố.

---

### User Story 4 - Không vượt hạn mức, luôn ưu tiên cảnh báo sự cố (Priority: P2)

Mỗi bot có 3.000 tin/tháng. HỏiCon đếm tin theo bot/tháng, cảnh báo đội ở 80%, dừng tin không khẩn ở 95%, nhưng tin
sự cố luôn được gửi; khi không gửi được bằng Zalo thì ghi trạng thái cần dự phòng.

**Why this priority**: Hết hạn mức giữa đợt thí điểm là mất đường cảnh báo.

**Independent Test**: Đặt bộ đếm gần ngưỡng trong test ⇒ kiểm tin không khẩn bị dừng, tin sự cố vẫn đi, trạng thái đúng.

**Acceptance Scenarios**:

1. **Given** bot đã dùng ≥ 95% hạn mức tháng, **When** có tin không khẩn, **Then** tin bị giữ lại với trạng thái
   "vượt ngưỡng", không gọi Zalo.
2. **Given** cùng tình huống, **When** có tin cảnh báo sự cố, **Then** tin vẫn được gửi.
3. **Given** Zalo lỗi hết số lần thử hoặc hết hẳn hạn mức, **Then** dòng tin có trạng thái "cần dự phòng" để kênh dự
   phòng (trang hành động — spec 023) xử lý.

---

### User Story 5 - Vận hành an toàn, kiểm thử không cần token (Priority: P3)

Đội đặt webhook bằng một lệnh chỉ in Đạt/Lỗi, chỉ phơi route webhook qua đường hầm, token không bao giờ xuất hiện trong
log, và toàn bộ test chạy ở chế độ mock trong CI.

**Why this priority**: Yêu cầu bảo mật bắt buộc của ADR-003; CI không có token.

**Independent Test**: Chạy bộ test ở chế độ mock không có token; quét log/test output không thấy token hay mã định danh
Zalo thô.

**Acceptance Scenarios**:

1. **Given** không có token, **When** chạy test, **Then** mọi test của tính năng chạy được và xanh.
2. **Given** webhook nhận secret sai hoặc thiếu, **Then** trả lỗi xác thực, không xếp job nào.
3. **Given** một lỗi HTTP khi gọi Zalo, **Then** lỗi ghi lại không chứa URL (token nằm trong URL).

---

### Edge Cases

- Webhook nhận khi DB tạm lỗi ⇒ trả lỗi để Zalo gửi lại (không trả 200 rồi mất cập nhật).
- Cập nhật không phải tin nhắn văn bản (ảnh, sticker, sự kiện khác) ⇒ bỏ qua có ghi đếm, không lỗi.
- Người giám hộ chặn bot / rời ⇒ gửi lỗi vĩnh viễn ⇒ không thử lại vô hạn, đánh dấu cần dự phòng.
- Hai người giám hộ (hạng 1, 2): T2 chuyển cho hạng 2 (đã có trong đồ thị) ⇒ đúng người nhận.
- Sự cố `is_demo`/`is_drill` ⇒ không bao giờ gửi tới người giám hộ thật ngoài phạm vi diễn tập đã đồng ý.
- Tháng mới ⇒ bộ đếm hạn mức về 0 theo `quota_month`.
- Nội dung do người giám hộ gõ là dữ liệu không tin cậy ⇒ không đưa vào LLM ở spec này, không log nguyên văn.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST nhận webhook tại `POST /webhooks/zalo/{bot_id}`, so khớp secret trong header bằng so sánh hằng
  thời gian, từ chối khi sai/thiếu mà không xếp việc.
- **FR-002**: Webhook MUST trả thành công nhanh và chuyển xử lý sang hàng đợi job; mỗi cập nhật được xử lý **đúng một lần**
  kể cả khi Zalo gửi lại.
- **FR-003**: Hệ thống MUST ghép người giám hộ bằng `/start <mã>` với mã 6 số, hết hạn 15 phút, dùng một lần; câu trả lời
  khi mã sai không tiết lộ mã có tồn tại.
- **FR-004**: Hệ thống MUST tạo được mã ghép đôi bằng lệnh vận hành cho môi trường dev/thí điểm (luồng từ app thuộc 020).
- **FR-005**: Job `notify_guardian` MUST gửi tin thật tới người giám hộ đúng hạng của gia đình sự cố, qua **một** client
  Zalo duy nhất, và ghi một dòng `messages_out` cho mỗi tin.
- **FR-006**: Mọi tin gửi đi MUST mở đầu "Đây là trợ lý AI HỏiCon." và có nhãn `[DIỄN TẬP]` khi là diễn tập (dùng lại
  `agents/texts.py`).
- **FR-007**: Hệ thống MUST đếm tin theo bot/tháng; ≥ 80% ⇒ cảnh báo đội; ≥ 95% ⇒ giữ tin không khẩn; tin sự cố luôn gửi.
- **FR-008**: Khi không gửi được (hết số lần thử, lỗi vĩnh viễn, hết hạn mức) MUST đặt trạng thái "cần dự phòng" trên
  dòng tin; không thử lại vô hạn.
- **FR-009**: Hệ thống MUST hiểu phản hồi 1/2/3 (và nút nếu nền tảng hỗ trợ), resume đồ thị sự cố đang chờ người giám hộ
  với quyết định tương ứng, và trả lời xác nhận; phản hồi không hiểu ⇒ hướng dẫn lại.
- **FR-010**: Định danh Zalo MUST NOT được lưu, log, in hay gửi LLM ở dạng thô; lưu theo D1 (mã hóa để gửi + HMAC để tra).
- **FR-011**: Token bot MUST NOT xuất hiện trong log, lỗi, trace hay output test (lọc `/bot…/`, lỗi không mang URL).
- **FR-012**: Hệ thống MUST có chế độ **mock** (mặc định khi không có token và trong CI) thay client thật, ghi lại tin đã
  "gửi" và cho phép giả lập cập nhật đến; chế độ thật chỉ bật khi có token và cấu hình rõ.
- **FR-013**: Đặt/xóa/kiểm webhook MUST qua lệnh vận hành chỉ in Đạt/Lỗi; đường hầm dev chỉ phơi ứng dụng con chứa route
  webhook (không phơi tài liệu API, OpenAPI, MCP).
- **FR-014**: Sự cố diễn tập/demo MUST mang cờ tới tận bên gửi; sự cố demo chỉ gửi tới gia đình demo.
- **FR-015**: Đội MUST có báo cáo spike `docs/spikes/P1-S3-zalo.md` (số đo giao tin, hạn mức thật, khả năng nút bấm,
  điều khoản nền tảng, quyết định kênh dự phòng) và **ADR-010** (gồm D1, D2) để Minh duyệt.

### Key Entities

- **Gia đình** (`families`), **Thành viên** (`members`: vai trò, bí danh xưng hô, hạng người giám hộ, định danh Zalo theo
  D1), **Mã ghép đôi** (`pairing_codes`: băm mã, hạn, đã dùng), **Tin gửi đi** (`messages_out`: kênh, bot, mẫu, trạng thái,
  tháng hạn mức, thời điểm, lỗi) — theo `docs/DATA-MODEL.md` §2, cột Zalo theo D1.
- **Cập nhật Zalo đến**: chỉ phần dùng tới (loại sự kiện, mã cập nhật, người gửi, văn bản/nút) — hợp đồng ở `docs/schemas/`.

## Bất biến an toàn *(mandatory)*

- **Dừng an toàn** (I): không đụng tới (máy chủ, sau đường găng).
- **LLM chỉ nâng** (III): không gọi LLM. Tin giai đoạn 1 là mẫu (`fast_alert`, ADR-009 quyết định 8). Văn bản người giám
  hộ gõ là không tin cậy, không đưa vào prompt.
- **Công khai AI** (IV): FR-006 cho mọi tin, kể cả trả lời `/start` và xác nhận phản hồi; có test.

## Quyền riêng tư & đồng ý *(mandatory)*

| Dữ liệu mới / thay đổi | Dạng lưu | Mục đích đồng ý (enum) | Hạn lưu | Gửi LLM? |
|---|---|---|---|---|
| `chat_id` Zalo của người giám hộ | mã hóa (D1) + HMAC tra cứu | `guardian_channel` — văn bản đồng ý ở spec 011/020 | đến khi rút đồng ý/xóa gia đình | Không |
| Nội dung tin gửi đi | trong payload job (30 ngày, DATA-MODEL §6) | như trên | 30 ngày | Không |
| Văn bản người giám hộ trả lời | **không lưu** — chỉ lưu quyết định đã phân loại | như trên | — | Không |
| Bộ đếm hạn mức | số đếm theo bot/tháng | không cần | lâu dài | Không |

Ràng buộc: bot **dev** chỉ dùng với tài khoản Zalo của Minh/Tiến (chưa có văn bản đồng ý — mục "Chặn phát hành").
Bot thí điểm chỉ bật sau spec 011/020.

## UX người cao tuổi *(mandatory nếu có màn hình hoặc câu chữ mới)*

Người nhận là người giám hộ (không phải người cao tuổi), nhưng câu chữ mới (trả lời `/start`, hướng dẫn 1/2/3, xác nhận)
theo giọng ấm, ngắn, có hành động cụ thể; `ux-elder-reviewer` duyệt mẫu tin (theo CLAUDE.md luật 16 cho mẫu tin Zalo).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Thời gian từ lúc xếp tin tới lúc Zalo xác nhận đã nhận p95 ≤ 5 000 ms — đo trên: bot dev thật, điện thoại
  Zalo của đội, n ≥ 20; kèm ≥ 5 lần bấm giờ tới khi tin hiện trên điện thoại.
- **SC-002**: Toàn bộ test của tính năng chạy ở chế độ mock, không cần token, < 60 s — đo trên: CI + máy dev.
- **SC-003**: 0 lần token hoặc định danh Zalo thô xuất hiện trong log, output test, bảng DB — đo trên: quét tự động
  sau bộ test + `privacy-audit` phạm vi backend.
- **SC-004**: Cùng một cập nhật gửi lại 5 lần ⇒ xử lý đúng 1 lần — đo trên: test tích hợp với Postgres.
- **SC-005**: Secret sai/thiếu ⇒ 100% bị từ chối, 0 job được xếp — đo trên: test.
- **SC-006**: 100% tin gửi đi (cảnh báo, nhắc, chuyển hạng, trả lời `/start`, xác nhận) mở đầu bằng câu công khai AI —
  đo trên: test.
- **SC-007**: Ở ≥ 95% hạn mức, 100% tin không khẩn bị giữ và 100% tin sự cố vẫn gửi — đo trên: test.
- **SC-008**: Mã ghép đôi quá 15 phút hoặc đã dùng ⇒ 100% bị từ chối — đo trên: test.

## Kế hoạch bằng chứng *(mandatory)*

- Output `uv run --directory backend ruff check . && uv run --directory backend pytest` (Postgres bật — integration chạy)
- Bảng số đo SC-001 (n, p50, p95, ngày, bot dev) trong `docs/spikes/P1-S3-zalo.md`; thiếu token ⇒ `BLOCKED`
- Kết quả quét token/định danh thô (SC-003)
- `security-privacy-reviewer` (Zalo + PII) và `ux-elder-reviewer` (mẫu tin) không còn High
- ADR-010 (nháp) + `docs/DATA-MODEL.md`, `docs/API.md` cập nhật

## Ngoài phạm vi & mốc cắt

- Ngoài phạm vi: trang hành động `/a/[token]` và đóng sự cố bằng quyết định người giám hộ (spec 023); ghép đôi từ app,
  văn bản đồng ý, `consents` (011/020); tóm tắt AI giai đoạn 2 (024); bản tin tuần (032); bảng `guardian_actions` (023).
- Nếu trễ, cắt trước: nút bấm (giữ trả lời 1/2/3); số đo bấm giờ trên điện thoại (giữ số phía máy chủ).
- Nếu Zalo thất bại về kỹ thuật/điều khoản: ADR-010 chốt kênh dự phòng (trang hành động; Telegram là phương án ADR-003).
- Nếu tới 05/11 chưa có token: SC-001 `BLOCKED`, báo cáo spike dùng số mock kèm nhãn "mock", không ☑.

## Assumptions

- Zalo Bot API theo mô tả ADR-003: token trên đường dẫn URL, secret qua header `X-Bot-Api-Secret-Token`, có `setWebhook`,
  `getMe`, gửi tin văn bản. Khả năng nút bấm và định dạng cập nhật **chưa xác minh** ⇒ research R1 trước khi code.
- Một bot dev (`hoicon-dev`) cho spike; nhiều bot (3) cho thí điểm cấu hình được theo `bot_id`.
- Đồ thị sự cố P1-S4 có thể nhận thêm `family_id` khi bắt đầu (thay đổi nhỏ, tương thích ngược) để biết người nhận;
  bảng `incidents` và `IncidentService` thuộc spec 021.
- `httpx` và `cryptography` đã có trong lockfile (phụ thuộc gián tiếp) ⇒ khai báo trực tiếp, không thêm thư viện mới.
