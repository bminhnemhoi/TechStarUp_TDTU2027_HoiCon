# Spec 031: Hồ sơ vụ việc — nhánh `case_file` + người giám hộ duyệt

**Mã ROADMAP**: `P2-16` · **Làn**: B (`backend/**`, `apps/web/**`, `docs/schemas/**`) · **Cột mốc**: MVP Vòng 2 (M3) · **Phụ thuộc**:
024 (đồ thị đầy đủ), 026 (`verifications`), 027 (web người giám hộ, phiên `hc_guardian`), 034 (hạn lưu, xóa theo yêu cầu) ·
**US**: US-07 ("Là con, tôi duyệt hồ sơ vụ việc trước khi gửi") · **ADR**: ADR-009 (một nhánh đồ thị mới, không đổi quyết định)
· **Danh sách cắt**: "DOCX hồ sơ vụ việc" (mục 2) ⇒ spec này **không** làm DOCX; bản in từ trình duyệt thay thế.

---

## 1. Bối cảnh

Khi người giám hộ quyết "nghi lừa đảo" (`scam`, `emergency_pause`), sự cố sang `case_open` rồi **dừng ở đó mãi**: không ai
chuyển `case_open → closed`, nên job hạn lưu của 034 (tính từ `closed_at`) không bao giờ xóa sự cố này. Thuyết minh hứa tác tử
"Hồ sơ" soạn hồ sơ vụ việc để gia đình mang đi trình báo. Bảng `case_files` có trong `DATA-MODEL.md` nhưng chưa có migration.

Ràng buộc riêng tư làm thay đổi hình dạng của "hồ sơ": máy chủ **không có** số điện thoại kẻ gian (chỉ HMAC + 3 số cuối), không
có số tài khoản, số tiền, tên ngân hàng. Một bản trình báo cần những thứ đó. Vì vậy hồ sơ = phần máy chủ biết (dòng thời gian,
mức rủi ro, dấu hiệu, kết quả tra cứu, câu trả lời của bác) + **ô để người giám hộ tự điền trên trình duyệt**, không gửi về máy chủ.

## 2. User story

| # | Ưu tiên | Câu chuyện |
|---|---|---|
| US-31.1 | **P1** | Là con, sau khi báo "nghi lừa đảo", tôi nhận tin Zalo rằng HỏiCon đã soạn sẵn hồ sơ, mở trang web thấy bản nháp có dòng thời gian, dấu hiệu, kết quả tra cứu |
| US-31.2 | **P1** | Là con, tôi duyệt (hoặc bỏ) bản nháp; chỉ bản đã duyệt mới in/sao chép được |
| US-31.3 | **P1** | Là con, tôi tự điền số điện thoại kẻ gian, số tài khoản đã chuyển, số tiền ngay trên trang để in, và biết chắc các ô này không gửi về HỏiCon |
| US-31.4 | **P2** | Là con, tôi đánh dấu "đã nộp cho công an/ngân hàng"; sự cố đóng lại và hồ sơ được giữ theo hạn lưu |
| US-31.5 | **P2** | Là đội, sự cố `case_open` không ai xử lý thì tự đóng sau 30 ngày, để hạn lưu chạy được |

## 3. Yêu cầu chức năng

- **(FR-001)** Hợp đồng trước: `docs/schemas/case_file.v1.json` (khung nhìn cho người giám hộ) và `case_file_action.v1.json` (thân
  lệnh) + fixture valid/invalid; test hợp đồng; sinh lại client TS.
- **(FR-002)** Migration (số kế tiếp sau head, chỉ làn B): bảng `case_files` — `id` uuid PK, `incident_id` FK `incidents` `CASCADE`
  **UNIQUE**, `family_id` FK `families` `CASCADE`, `status` CHECK ∈ {`draft`, `approved`, `sent`, `discarded`}, `content` jsonb (chỉ
  đúng `case_file.v1#/$defs/content`), `summary_source` CHECK ∈ {`template`, `llm`}, `approved_by` FK `members` `SET NULL`,
  `approved_at`, `sent_at`, `discarded_at`, `created_at`, `is_demo`; chỉ mục `(family_id, created_at)`. `is_drill` **không** có: diễn
  tập không bao giờ sinh hồ sơ. Test lên/xuống migration.
- **(FR-003)** Đồ thị: sau `resolve`, nếu kết cục là `case_open`, có sự cố thật, `is_drill = false` ⇒ nút `case_file` rồi interrupt
  `await_case_approval`; các kết cục khác ⇒ `END` như cũ. Diễn tập, eval (`incident_id` không phải UUID) và sự cố mô phỏng của 033
  (cờ `sim`) đi thẳng `END`, không tạo dòng `case_files`. Gia đình demo không qua sim (seed E2E của 027) **có** hồ sơ, mang
  `is_demo = true`, để test web chạy được.
- **(FR-004)** Nút `case_file` dựng `content` **tất định** từ dữ liệu đã có: dòng thời gian từ `incident_transitions` (giờ + nhãn
  tiếng Việt cố định), mức rủi ro + lý do (khóa enum ⇒ câu cố định), luật trên máy (`rule_id` ⇒ câu cố định), loại ứng dụng, 3 số
  cuối, câu trả lời E8, kết quả `verifications` (loại, phán quyết, tên nguồn, phiên bản danh sách), quyết định của người giám hộ.
  Không có số điện thoại đầy đủ, h1, HMAC, tên gói, lời kể tự do, tên thật.
- **(FR-005)** Đoạn "Tóm tắt diễn biến" (tùy chọn): một lời gọi `llm_router` hồ sơ `fast` *(23/10: chốt `fast`, plan D11; trước ghi `strong`)* (che PII, `<untrusted>` không cần vì
  không có văn bản của kẻ gian, timeout ≤ 4 s, output có cấu trúc `{summary}` ≤ 600 ký tự). Lọc: không chữ số dài ≥ 4, không
  link/tên miền/kênh chat (dùng lại bộ lọc `_UNSAFE_SUMMARY`), không lời khuyên nguy hiểm (`unsafe_advice` của 036 nếu đã có);
  hỏng/quá hạn/không khóa ⇒ câu mẫu dựng từ dữ kiện; ghi `summary_source`. Đoạn này mở đầu bằng "Đây là trợ lý AI HỏiCon" và
  nhãn "do trợ lý AI soạn — anh/chị đọc kỹ trước khi duyệt". Đồ thị ghi `agent_steps.node = "case_file"`.
- **(FR-006)** Một tin Zalo (mẫu, `urgent=True` vì gắn sự cố, đi `messages_out`, khóa chống trùng `{incident}:msg:case_file`) báo
  người giám hộ đã có bản nháp và cách mở (nhắn "4" để nhận liên kết đăng nhập web — 027). Mở đầu "Đây là trợ lý AI HỏiCon".
  Không có liên kết chứa token trong tin này.
- **(FR-007)** API người giám hộ (phiên `hc_guardian`, chỉ sự cố gia đình mình, sai gia đình ⇒ 404): `GET
  /v1/guardian/incidents/{id}/case-file` ⇒ `case_file.v1`; `POST …/case-file` thân `case_file_action.v1` (`approve` | `discard` |
  `mark_sent`) qua `require_same_origin`. Chuyển trạng thái hợp lệ: `draft → approved | discarded`, `approved → sent | discarded`;
  sai ⇒ 409. `approve`/`discard` resume đồ thị (`expect="await_case_approval"`); `mark_sent` và `discard` chuyển sự cố `case_open →
  closed` qua `IncidentService.transition()` (actor `guardian`). Mọi lệnh ghi `agent_steps`/`incident_transitions`, không ghi nội
  dung ô tự điền.
- **(FR-008)** Đóng tự động: job hằng ngày chuyển sự cố `case_open` không có hoạt động 30 ngày ⇒ `closed` (actor `system`), hồ sơ
  `draft` ⇒ `discarded`; hồ sơ `approved`/`sent` giữ nguyên trạng thái. Test với đồng hồ giả.
- **(FR-009)** Hạn lưu và xóa: `case_files` xóa cùng sự cố (CASCADE, 12 tháng từ `closed_at`, DATA-MODEL §6 thêm dòng); xóa gia
  đình theo yêu cầu (034 `purge_service`) xóa hết `case_files`; test cho cả hai.
- **(FR-010)** Web `/incidents/[id]/case-file`: hiện bản nháp/đã duyệt; nút "Duyệt hồ sơ" và "Bỏ hồ sơ" có xác nhận; sau duyệt mới
  hiện "In / lưu PDF" (`window.print()`, CSS in riêng) và "Sao chép chữ"; nhóm ô **tự điền** (số điện thoại đã gọi tới, số tài khoản
  đã chuyển, số tiền, giờ chuyển, ngân hàng) là `input` **không nằm trong form gửi đi**, không lưu `localStorage`, có dòng giải thích
  "Các ô này chỉ nằm trên máy của anh/chị, HỏiCon không nhận được". Link từ trang chi tiết sự cố khi có hồ sơ.
- **(FR-011)** Hướng dẫn trình báo: danh sách bước trong `data/case_file/report_guidance.vi.yaml` (`approved: false` tới khi Minh
  duyệt; bản prod chỉ hiện hướng dẫn khi `approved: true`, nếu không thì hiện "Anh/chị liên hệ công an nơi cư trú và ngân hàng của
  người thân"). **Không** ghi số điện thoại đường dây nóng nào khi chưa có nguồn chính thức đã kiểm.
- **(FR-012)** Văn bản đồng ý: thêm vào `docs/legal/consent/guardian_alerts.vi.md` một câu về hồ sơ (soạn sẵn để con bác mang đi
  trình báo nếu muốn; HỏiCon không tự gửi cho cơ quan nào), giữ ≤ 160 từ (test 011), chạy `consent_texts write`; làn A ghim lại sha.
  Câu này chỉ thêm **cùng PR** với mã thực thi.
- **(FR-013)** Hồi quy eval: bộ `smoke` (và `full` nếu 036 đã có) **không đổi chỉ số** — eval không có sự cố thật nên đi thẳng `END`
  (FR-003). Vì vậy độ sạch của hồ sơ **không** đo bằng eval mà bằng pytest trên sự cố seed: chạy đồ thị thật với `ReplayClient` cho
  ≥ 5 kịch bản lừa đảo của `data/scenarios/` (gồm ≥ 2 ca chèn lệnh) tới `case_open`, kiểm `content` + tin không chứa `case_secrets`,
  có `ai_label`, tóm tắt qua bộ lọc. *(Sửa 18/10 khi rà analyze: bản đầu đòi eval kiểm hồ sơ, mâu thuẫn với FR-003.)*
- **(FR-014)** Kiểm chứng & tài liệu: pytest, Playwright (duyệt, bỏ, in, ô tự điền không đi qua mạng — chặn bằng
  `page.on("request")` và kiểm thân mọi yêu cầu), axe 0 lỗi, ảnh 360/1280 px; `security-privacy-reviewer`, `ux-elder-reviewer`
  (câu chữ cho người giám hộ); `docs/AGENTS.md`, `docs/DATA-MODEL.md`, `docs/API.md`, `docs/PRIVACY-DPIA.md`.

- **(FR-015)** *(Wave 4, 23/10/2026)*: `GET /v1/guardian/incidents/{id}/case-file` gửi `guidance` (hợp đồng `case_file.v1`): đọc
  `data/case_file/report_guidance.vi.yaml`; `approved: false` ⇒ `steps: []` + `fallback_vi`; `approved: true` ⇒ mọi bước (`id`,
  `text_vi`, `source_ref`). Trang hồ sơ hiện mục "Các bước nên làm" từ trường này (khối riêng, **không** in như dữ kiện vụ việc). Không
  hiện số đường dây nóng nào không có trong tệp đã duyệt.

## 4. Tiêu chí thành công

| Mã | Tiêu chí | Ngưỡng | Nguồn đo |
|---|---|---|---|
| **(SC-001)** | Có hồ sơ khi nghi lừa đảo | 100% sự cố thật kết cục `case_open` có 1 dòng `case_files` `draft` + 1 tin Zalo; 0 hồ sơ cho diễn tập/eval/sim | pytest đồ thị + DB |
| **(SC-002)** | Không PII | 0 số điện thoại/h1/HMAC/tên gói/lời kể trong `case_files.content`, tin Zalo, `agent_steps` | pytest quét `case_secrets` |
| **(SC-003)** | Ô tự điền không rời máy | 0 yêu cầu mạng chứa giá trị ô tự điền trong lúc điền, duyệt, in | Playwright |
| **(SC-004)** | Máy trạng thái hồ sơ | mọi cặp chuyển trạng thái hợp lệ/không hợp lệ đúng (200/409); sự cố đóng khi `mark_sent`/`discard` | pytest |
| **(SC-005)** | Hạn lưu chạy được | `case_open` 30 ngày ⇒ `closed`; 12 tháng sau ⇒ sự cố + hồ sơ bị xóa; xóa gia đình ⇒ 0 hồ sơ | pytest đồng hồ giả |
| **(SC-006)** | LLM không bắt buộc | không khóa ⇒ hồ sơ vẫn đủ, `summary_source = template`; LLM trả số/link ⇒ thay bằng mẫu | pytest + `ReplayClient` |
| **(SC-008)** | Hướng dẫn trình báo lên web | Chưa duyệt ⇒ trang chỉ hiện câu chung, 0 bước; đã duyệt ⇒ đủ bước theo thứ tự tệp, có nguồn; phản hồi khớp `case_file.v1.guidance` | pytest + Playwright |
| **(SC-007)** | Người giám hộ thật dùng được | 1 người giám hộ thí điểm duyệt + in hồ sơ, nói lại được nội dung | **BLOCKED** (thí điểm, 029 giai đoạn 2) |

## 5. Làm rõ (clarify, 18/10/2026 — tự quyết)

| # | Điểm mơ hồ | Quyết định | Lý do |
|---|---|---|---|
| Q1 | "Gửi" hồ sơ cho ai? | HỏiCon **không** gửi cho cơ quan nào; `sent` = người giám hộ tự đánh dấu đã nộp | PRD: ngoài phạm vi tích hợp cơ quan/ngân hàng; trang chi tiết 027 đã hứa "không tự báo cho cơ quan nào" |
| Q2 | Số điện thoại kẻ gian ở đâu? | Ô tự điền trên trình duyệt, không gửi máy chủ | ADR-006: máy chủ chỉ có HMAC + 3 số cuối |
| Q3 | LLM có viết cả hồ sơ? | Không; chỉ đoạn tóm tắt tùy chọn, có lọc, có nhãn; phần dữ kiện là tất định | Văn bản đi tới cơ quan phải đúng sự thật; giữ lời hứa "tác tử Hồ sơ" của thuyết minh |
| Q4 | Mục đích đồng ý mới? | Không thêm enum; ghi vào `guardian_alerts` (cùng người nhận, cùng dữ liệu, HỏiCon không chia sẻ thêm) — **★ Minh xác nhận phạm vi DPIA** | Luật 7 chỉ bắt enum mới khi mục đích mới; ghi ở MASTER-PLAN §8 |
| Q5 | Sự cố `case_open` bao giờ đóng? | Người giám hộ `mark_sent`/`discard`, hoặc tự đóng sau 30 ngày | Không đóng ⇒ hạn lưu 12 tháng không bao giờ chạy (lỗi hiện có) |
| Q6 | DOCX? | Không (danh sách cắt mục 2); in từ trình duyệt | Ít code, không thêm thư viện |

## 6. Ngoài phạm vi

DOCX/PDF sinh ở máy chủ; gửi hồ sơ tự động; đính kèm ảnh chụp màn hình; chỉnh sửa nội dung dữ kiện của hồ sơ (chỉ duyệt/bỏ);
người cao tuổi xem hồ sơ trên app.
