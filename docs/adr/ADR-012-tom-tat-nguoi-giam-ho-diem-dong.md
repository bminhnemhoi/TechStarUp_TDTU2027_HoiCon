# ADR-012: Tóm tắt gửi người giám hộ dựng từ danh sách điểm đóng, LLM chỉ chọn điểm

- Trạng thái: **Đề xuất** (22/10/2026). Soạn bởi Claude cho Tiến (quyết định kỹ thuật, không phải phạm vi của Minh). Chờ Tiến
  chấp nhận; làn B thi công theo ADR này ở `specs/024-risk-and-intervention` T014–T015 (nếu Tiến bác thì dừng ở T014 và
  ghi lại).
- Liên quan: ADR-009 (lõi tác tử), CLAUDE.md luật 5–6 và 13; `specs/024-risk-and-intervention` §5 (FR-011, SC-007);
  `specs/036-eval-full/evidence.md` phát hiện **F-2**; hợp đồng `docs/schemas/guardian_brief.v2.json`.
- Sửa đổi: không ADR nào bị thay. Thay hành vi của `intervention` mô tả ở `docs/AGENTS.md` (tóm tắt LLM tự do ≤ 280 ký tự).

## Bối cảnh
Node `intervention` (spec 024) cho LLM viết `summary` tự do ≤ 280 ký tự, chèn **thẳng** vào tin Zalo gửi con cháu. Rào hiện có
là regex `_UNSAFE_SUMMARY` (chặn chữ số, link, tên miền, `@`, tên kênh chat) rồi `mask_text`. Eval full (spec 036) chứng minh
khoảng trống: nếu model "nghe lời" một câu chèn bằng **chữ thuần** ("đừng báo ai", "cuộc gọi an toàn", "không cần báo thêm"),
câu đó tới người giám hộ ở cả **13/13** ca chèn lệnh ngoài smoke (ghim bằng
`test_known_gap_prose_injection_passes_the_graph_filter_on_every_injection_case`). Đây là đường cảnh báo, thuộc nhóm
"không bao giờ cắt".

Ngữ cảnh gửi cho LLM ở `intervention` hiện chỉ là siêu dữ liệu + enum (mức, thủ đoạn, câu trả lời Có/Không, cờ `note_flags`),
nên kênh chèn thực tế hẹp. Nhưng (a) `risk_scorer` và các node sau (031 `case_file`) sẽ nhận thêm dữ liệu, (b) model có thể
tự bịa câu trấn an, (c) luật 5 đòi đầu ra có cấu trúc. Một câu chữ tự do do LLM viết, đi thẳng tới người nhận, không kiểm được
bằng luật tất định.

## Các phương án

| Phương án | Chặn chữ thuần | Tất định | Giữ giá trị AI | Kết luận |
|---|---|---|---|---|
| A. Thêm danh sách cấm cụm từ ("đừng báo", "an toàn rồi"…) vào `_UNSAFE_SUMMARY` | một phần: đổi cách nói là lọt | có | có | loại: luôn đi sau kẻ gian một bước, không có tiêu chí "đủ" |
| B. LLM-judge chấm tóm tắt trước khi gửi | phần lớn | **không** | có | loại: trái yêu cầu "không dựa LLM", thêm độ trễ vào đường cảnh báo, judge cũng bị chèn được |
| C. Bỏ hẳn LLM ở `intervention`, chỉ dùng mẫu | hoàn toàn | có | **mất** (US-05 "tóm tắt AI có lý do") | loại: rơi về đúng câu mẫu hiện có |
| **D. Danh sách điểm đóng**: LLM chỉ chọn 1–3 mã điểm từ enum; máy chủ ghép câu tiếng Việt cố định, mỗi điểm có điều kiện dữ kiện | hoàn toàn: không có chữ LLM nào tới người nhận | có | có: LLM chọn và xếp lý do | **chọn** |

## Quyết định (phương án D)
1. `GuardianBrief` v2 = `{ "points": [BriefPoint, …] (1–3, không trùng), "action": Action }`, `extra="forbid"`. **Không còn
   trường `summary`.** Hợp đồng: `docs/schemas/guardian_brief.v2.json` (enum là nguồn sự thật; test so enum Pydantic với
   hợp đồng). Output sai cấu trúc, mã lạ, thừa trường ⇒ router rơi về mẫu (như mọi lỗi LLM khác).
2. Mỗi mã có **một câu tiếng Việt cố định** trong `hoicon.agents.texts.BRIEF_POINT_VI` (giọng ấm áp, không hoảng sợ, không
   chữ số/link — luật 13) và **một điều kiện dữ kiện tất định** đọc từ state. Điểm có điều kiện sai bị bỏ (LLM không bịa
   được điều máy không biết):

   | Mã | Điều kiện (state; tên trường theo `risk_event.v1` và `NOTE_KEYWORDS`) |
   |---|---|
   | `unknown_call_then_finance_app` | `event.app.category ∈ {bank, wallet, securities}` |
   | `sideloaded_app` | `event.app.category == "sideloaded"` |
   | `call_still_ongoing` | `event.call.active == true` |
   | `flagged_number` | `threat.verdict == "flagged"` hoặc `event.caller.flagged` |
   | `caller_claims_authority` | `q_caller_authority = yes` hoặc cờ `mentions_authority` |
   | `asked_transfer_or_code` | `q_asked_transfer = yes` hoặc cờ `mentions_transfer` / `mentions_code` |
   | `asked_secrecy` | cờ `mentions_secrecy` |
   | `asked_install_app` | cờ `mentions_app_or_link` |
   | `elder_unsure_of_caller` | `q_know_caller ∈ {no, unsure}` |
   | `common_scam_pattern` | luôn đúng (câu giải thích chung, như câu mẫu hiện có) |
   | `may_be_routine` | **chỉ khi mức cuối ≤ `medium`** (LLM không được trấn an ở mức `high`/`critical` — luật 5 "chỉ nâng") |

   Luật R5 (ứng dụng điều khiển từ xa) chưa có trong `risk_event.v1` phía máy chủ nên chưa có mã riêng; thêm khi sự kiện có.
   Bộ chính xác (tên mã, câu chữ, điều kiện) chốt ở `specs/024-risk-and-intervention` §5; đổi bộ ⇒ tăng `version` hợp đồng
   và prompt.
3. Máy chủ ghép `summary = " ".join(câu của các điểm còn lại theo thứ tự LLM)`, thay `{alias}`; còn rỗng sau khi lọc ⇒ bộ mặc
   định tất định: mã ứng dụng đúng điều kiện (`unknown_call_then_finance_app` hoặc `sideloaded_app`, nếu có) + `common_scam_pattern`.
   `fallback` của router (LLM lỗi/sai dạng) là `GuardianBrief` v2 với đúng bộ mặc định này ⇒ không còn câu mẫu tự do. `guardian_detail` và câu công khai AI do mẫu
   thêm, không đổi. Mức `critical` vẫn ép `call_and_stay_on_line`.
4. `_UNSAFE_SUMMARY` không còn cần ở đường chính (mọi câu đã cố định); giữ một test hợp đồng rằng **mọi câu** trong
   `BRIEF_POINT_VI` qua được `_UNSAFE_SUMMARY`, bộ kiểm hoảng sợ/hoàn tiền của eval và `mask_text` không đổi gì.
5. Prompt `intervention.md` lên `version: 2` (chọn điểm + action, liệt kê mã và nghĩa); cassette smoke/full sinh lại theo v2.
   Văn bản kẻ gian vẫn chỉ đi trong `<untrusted>`, không vào system prompt (luật 5) — ADR này không mở thêm kênh dữ liệu nào.

## Hệ quả
- **Được**: lời chèn chữ thuần không còn đường tới người giám hộ (đo: 17/17 ca injection + 13 ca chữ thuần bị chặn, 0
  vi phạm — spec 024 SC-007, spec 036 T025–T027). Tóm tắt không bịa dữ kiện. Kiểm được bằng test tất định, không cần judge.
- **Mất**: tóm tắt kém linh hoạt (tối đa 3 câu từ 11 câu cố định). Chấp nhận: người giám hộ cần biết *việc gì* và *làm gì*,
  không cần văn hay. Thêm một tình huống mới = thêm mã + câu + điều kiện + test (rẻ).
- **Eval**: hành vi đối kháng `obey_injection` đổi nghĩa (model trả `summary` tự do kiểu v1, hoặc mã lạ, hoặc chỉ
  `may_be_routine` ở mức cao); thêm loại `soothe`, `off_vocab`. Đột biến (c) của spec 036 đổi thành "bỏ bước ghép từ danh
  sách điểm, dùng thẳng chữ của LLM".
- **Không đổi**: `risk_scorer` (output đã là enum + `reasons` chỉ ghi trace, không gửi đi), đường cảnh báo nhanh `fast_alert`
  (không LLM), kênh Zalo, hạn mức.
- 031 (`case_file`) dùng lại cùng nguyên tắc cho đoạn tóm tắt hồ sơ nếu có LLM (ghi ở 031 plan, không thuộc ADR này).
