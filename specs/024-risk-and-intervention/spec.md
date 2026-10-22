# Spec 024: Đánh giá rủi ro, Ngân hàng câu hỏi E8 & Tác tử can thiệp (Risk Scorer, E8 & Intervention Agent)

**Mã ROADMAP**: `P2-08` + `P2-09` · **Làn sở hữu**: Làn A (Android) + Làn B (Server) · **Phụ thuộc**: `021-events-incident-service`, `023-guardian-alert`, `030-eval-smoke` · **Cột mốc**: **Gate M1 / M2** · **Nhánh tính năng**: `feat/024-risk-and-intervention`

---

## 1. Mục tiêu & Bối cảnh

Spec 024 hoàn thiện "bộ não tác tử can thiệp" của HỏiCon — kết hợp sức mạnh phân tích đa tầng giữa luật tất định trên máy (mức sàn `rule_floor`), đe dọa từ cơ sở dữ liệu (`threat_indicators`), tương tác trực tiếp với người cao tuổi qua màn hình câu hỏi nhanh E8 trên app Lính gác (đẩy qua FCM / API), và mô hình ngôn ngữ lớn (LLM `risk_scorer` + `intervention`) để đưa ra khuyến nghị can thiệp chính xác tới người thân (người giám hộ).

Tác tử can thiệp vận hành dựa trên đồ thị trạng thái LangGraph bền vững (`IncidentRuntime`), hỗ trợ ngắt (`interrupt`) hai lần:
1. `ask_elder`: hỏi người cao tuổi khi cần xác minh nghi vấn (có hẹn giờ 60s).
2. `await_guardian`: chờ quyết định can thiệp từ người giám hộ, kèm bộ hẹn giờ tự động T1 (120s nhắc người giám hộ 1), T2 (300s chuyển người giám hộ 2), T3 (900s dừng chờ kết thúc sự cố).

Đặc tả này hiện thực trọn vẹn User Story **US-05** ("Là con, tôi thấy tóm tắt AI và đánh giá rủi ro có lý do trong $\le 15\text{ s}$") và bảo vệ tính mạng / tài sản của người cao tuổi theo triết lý "LLM chỉ nâng mức rủi ro, không bao giờ hạ thấp hơn mức sàn".

---

## 2. Tiêu chí thành công (Success Criteria)

- **(SC-001)**: Thời gian từ khi nhận lô sự kiện đến khi hoàn tất tóm tắt AI can thiệp (`intervention`) tới người giám hộ đạt $p95 \le 15\text{ s}$ (bao gồm cả điều phối đồ thị và thời gian gọi LLM, với trần cứng LLM 4s; quá hạn tự động rơi về mẫu an toàn).
- **(SC-002)**: Độ chính xác đánh giá rủi ro: Đồ thị tuân thủ nghiêm ngặt bất biến `level >= rule_floor` tại mọi thời điểm; khi người cao tuổi trả lời "Có" cho câu hỏi nghi vấn (ví dụ giả danh công an / đòi chuyển tiền), mức rủi ro bắt buộc được nâng lên `high` hoặc `critical`.
- **(SC-003)**: Ngân hàng câu hỏi E8: 100% câu hỏi gửi xuống app Lính gác mở đầu bằng câu công khai AI (`Đây là trợ lý AI HỏiCon.`), có cờ diễn tập `[DIỄN TẬP]` nếu là sự cố diễn tập, và chỉ chấp nhận 3 câu trả lời tất định: `yes`, `no`, `unsure` (tuyệt đối không lưu ghi âm hay văn bản tự do của người cao tuổi trên máy chủ — ADR-009).
- **(SC-004)**: Màn hình Compose E8 trên Android hiển thị chữ to rõ, độ tương phản cao đạt chuẩn WCAG AAA $\ge 7:1$, 3 nút bấm kích thước $\ge 64\text{dp}$, hỗ trợ đọc câu hỏi bằng giọng nói offline (TTS) và tự động đóng/gửi timeout sau 60s.
- **(SC-005)**: Bộ hẹn giờ tự động T1 (120s), T2 (300s), T3 (900s) hoạt động tin cậy qua hàng đợi `jobs` với khóa chống trùng `idempotency_key`, sống sót qua sự cố tiến trình (kill -9) và không giẫm lên quyết định thủ công của người giám hộ.
- **(SC-006)**: Không làm suy giảm độ chính xác trên bộ kiểm thử đánh giá: Chạy `hoicon-eval smoke` (Spec 030) đạt recall leo thang $\ge \text{baseline}$, tỷ lệ báo nhầm $\le \text{baseline}$, 0 vi phạm an toàn và 100% công khai AI.

---

## 3. Yêu cầu chức năng (Functional Requirements)

- **(FR-001)**: Ban hành JSON Schema hợp đồng `docs/schemas/elder_question.v1.json` và `docs/schemas/elder_answer.v1.json` kèm các bộ fixtures valid/invalid.
- **(FR-002)**: Hiện thực kênh đẩy thông báo FCM `hoicon.channels.fcm` (hỗ trợ chế độ dry-run/mock khi chưa có cấu hình Firebase thật) để chuyển phát yêu cầu câu hỏi E8 tới app Android.
- **(FR-003)**: Xây dựng endpoint `POST /v1/incidents/{id}/answers` nhận câu trả lời E8 từ thiết bị Android, xác thực JWT thiết bị cùng gia đình, kiểm tra tính hợp lệ và gọi `IncidentRuntime.resume(expect="ask_elder")`.
- **(FR-004)**: Xây dựng endpoint `GET /v1/incidents/{id}/pending-question` cho phép app Lính gác truy vấn câu hỏi E8 đang chờ xử lý của sự cố (phục vụ fallback khi FCM chậm hoặc mất mạng).
- **(FR-005)**: Nâng cấp đồ thị `incident_graph.py` và `IncidentRuntime`: tích hợp `risk_scorer` đánh giá lại sau khi có câu trả lời E8, sinh tóm tắt AI trong `intervention`, kích hoạt bộ hẹn giờ T1/T2/T3 tại `await_guardian`, và map đúng kết quả `scam` sang `case_open` tại `resolve`.
- **(FR-006)**: Tự động kết nối kích hoạt đồ thị tác tử từ `POST /v1/events`: khi `IncidentService.correlate_event` mở sự cố mới hoặc nâng mức rủi ro, tự động khởi tạo hoặc đánh thức đồ thị tương ứng.
- **(FR-007)**: Xử lý bộ hẹn giờ đồ thị trong worker `hoicon.jobs.worker`: thực thi job `graph_resume` khi timer T1 (gửi tin nhắc `reminder`), T2 (gửi tin leo thang `escalation` cho người giám hộ rank 2), T3 (dừng chờ `resolved_no_response`) hoặc timeout E8 đến hạn.
- **(FR-008)**: Thiết kế và triển khai màn hình Compose E8 (`ElderQuestionScreen.kt` & `ElderQuestionActivity.kt`) trên Android với 3 nút bấm kích thước lớn ("Có", "Không", "Không rõ"), nhãn công khai AI, nhãn `[DIỄN TẬP]`, và giọng đọc TTS offline.
- **(FR-009)**: Hiện thực `ElderApiClient` trên Android gửi câu trả lời `POST /v1/incidents/{id}/answers` kèm cơ chế thử lại an toàn khi mạng chập chờn.
- **(FR-010)**: Viết bộ test tích hợp toàn diện: test hợp đồng schemas E8, test đồ thị LangGraph với chuỗi hẹn giờ T1/T2/T3, test API answers, test UI Compose E8 trên Android, và kiểm chứng bằng chứng trên `hoicon-eval smoke`.

---

## 4. Điều chỉnh khi rà soát (16/10/2026)

- **ADR-006**: job `start_graph` không còn mang `caller.h1`/`app.package` (bảng `jobs` giữ dòng đã chạy); danh sách đe dọa
  được tra ngay ở `POST /v1/events` (`prepare_event`). Chạy lại job không mở lượt đồ thị thứ hai.
- **FR-006**: đồ thị khởi động khi sự cố đạt `high`/`critical` (cùng ngưỡng cảnh báo nhanh của spec 023), không phải mọi
  sự cố mở mới — tránh gửi Zalo cho sự cố mức thấp.
- **FR-005/FR-007**: người giám hộ quyết ngoài đồ thị (`/a/`, JWT, Zalo) ⇒ `intervention`/`await_guardian` không gửi thêm
  tin; `resolve` ghi kết quả đồ thị qua `IncidentService` (`close_from_graph`): T3 ⇒ `resolved_no_response`, "lừa đảo" ⇒
  `case_open`. Eval: kết cục mong đợi của ca lừa đảo đổi thành `case_open` (`eval_report.v1.json` thêm giá trị).
- **FR-003**: câu trả lời E8 xếp job `graph_resume`, không chạy LLM trong request; `question_id` phải khớp câu đang hỏi.
  `note_flags` dùng đúng bộ cờ `NOTE_KEYWORDS`.
- **ADR-002**: worker job chạy nền trong tiến trình API (trước đó API không chạy job nào); runtime mở lười.
- **FR-002**: FCM chỉ mock (chưa có Firebase), data message chỉ mang mã; nội dung câu hỏi lấy qua `pending-question`.
- **FR-008/FR-009**: E8 chữ ≥ 20sp, vùng chạm ≥ 64dp, tương phản ≥ 7:1, nút ghim đáy ở cỡ chữ 200%; gửi qua WorkManager.

---

## 5. Wave 3 (22/10/2026) — hai phát hiện của eval full (spec 036 F-1, F-2)

**Vì sao ở spec này, không ở 036:** cả hai nằm trong mã spec 024 sở hữu (FR-005: `intervention` sinh tóm tắt, `risk_scorer` +
`_ANSWER_FLOOR`). Spec 036 là dụng cụ đo và tự cấm sửa đồ thị/prompt (tasks.md 036, "Chế độ chạy"); để eval vừa sửa vừa chấm
chính mình thì mất tính độc lập. 036 nhận phần đo: ca hồi quy + tiêu chí (036 FR-013, T025–T028).

### F-2 — lời chèn bằng chữ thuần lọt bộ lọc tóm tắt (AN TOÀN, "không bao giờ cắt": đường cảnh báo)

- **(FR-011)**: `intervention` không còn đưa chữ tự do của LLM tới người giám hộ (ADR-012). LLM trả `GuardianBrief` v2
  (`docs/schemas/guardian_brief.v2.json`): 1–3 mã `points` từ danh sách đóng + `action`; `extra="forbid"`. Máy chủ (tất
  định): (a) bỏ mã có điều kiện dữ kiện sai (bảng dưới); (b) bỏ `may_be_routine` khi mức ≥ `high`; (c) ghép câu cố định
  `texts.BRIEF_POINT_VI` theo thứ tự LLM, thay `{alias}`; (d) rỗng ⇒ bộ mặc định = mã ứng dụng đúng điều kiện (nếu có) +
  `common_scam_pattern`; (e) output sai dạng/mã lạ/thừa trường ⇒ router trả `fallback`, mà `fallback` giờ cũng là `GuardianBrief` v2
  (`points` = bộ mặc định, `action` theo mức) — **không còn câu mẫu tự do nào**: mọi tin `detail` chỉ gồm câu `BRIEF_POINT_VI`. Prompt
  `intervention.md` lên `version: 2`. Văn bản kẻ gian vẫn chỉ trong `<untrusted>`; LLM vẫn chỉ nâng mức (không đổi `raise_only`).
- **(SC-007)**: Không chữ nào do LLM viết có mặt trong tin gửi người giám hộ: (i) suite `injection` **17/17 ca bị chặn, 0 vi
  phạm**; (ii) 13 ca chèn chữ thuần (cassette của test ghim F-2) **13/13 không lọt**, test ghim đảo chiều; (iii) mọi tin
  `detail` của lượt full chỉ gồm câu trong `BRIEF_POINT_VI` (kiểm `brief_outside_vocabulary` của 036); (iv) smoke/full không
  tụt so baseline (recall, báo nhầm), 0 vi phạm, công khai AI 100%.

Câu chữ chốt (người đọc là con cháu, "anh/chị"; `{alias}` = cách xưng hô người cao tuổi; không chữ số/link; `ux-elder-reviewer`
đọc lại ở T015):

| Mã | Câu (`BRIEF_POINT_VI`) | Điều kiện |
|---|---|---|
| `unknown_call_then_finance_app` | {alias} vừa nghe một số lạ gọi rồi mở ứng dụng ngân hàng hoặc ví tiền. | `app.category ∈ {bank, wallet, securities}` |
| `sideloaded_app` | {alias} vừa mở một ứng dụng cài từ ngoài cửa hàng Play sau cuộc gọi lạ. | `app.category == sideloaded` |
| `call_still_ongoing` | Cuộc gọi lạ có thể vẫn đang diễn ra. | `call.active == true` |
| `flagged_number` | Số gọi tới nằm trong danh sách cảnh báo lừa đảo. | `threat.verdict == flagged` hoặc `caller.flagged` |
| `caller_claims_authority` | Người gọi xưng là công an, ngân hàng hoặc cơ quan nhà nước. | `q_caller_authority = yes` hoặc cờ `mentions_authority` |
| `asked_transfer_or_code` | Người gọi bảo {alias} chuyển tiền hoặc đọc mã số. | `q_asked_transfer = yes` hoặc cờ `mentions_transfer`/`mentions_code` |
| `asked_secrecy` | Người gọi dặn {alias} giữ kín, đừng kể với người nhà. | cờ `mentions_secrecy` |
| `asked_install_app` | Người gọi bảo {alias} cài ứng dụng hoặc mở đường dẫn lạ. | cờ `mentions_app_or_link` |
| `elder_unsure_of_caller` | {alias} không chắc người gọi là ai. | `q_know_caller ∈ {no, unsure}` |
| `common_scam_pattern` | Đây là dấu hiệu thường gặp khi kẻ gian giả danh để dụ chuyển tiền. | luôn đúng |
| `may_be_routine` | Có thể chỉ là việc bình thường, anh/chị cứ hỏi thăm nhẹ nhàng. | mức cuối ≤ `medium` |

### F-1 — người cao tuổi xác nhận "bị đòi chuyển tiền" ⇒ luôn `critical` (báo nhầm) — **★ chờ Minh** (MASTER-PLAN §8 mục 8)

**Đúng hay sai theo luật?** *Đúng luật.* `("q_asked_transfer","yes") ⇒ critical` là mức sàn **tất định** từ câu trả lời của
người cao tuổi; luật 5 cấm LLM hạ mức, không cấm luật tất định thận trọng. Nó không phải lỗi an toàn mà là **hiệu chỉnh gây
báo nhầm**: 10/37 ca hợp lệ (con gửi học phí, tiền nhà, shipper thu hộ…) đều xác nhận "có người bảo chuyển tiền". Mọi cách sửa
phải giữ tất định; **cấm** sửa bằng cách cho LLM hạ dưới mức do câu trả lời đặt ra.

| Phương án | Báo nhầm xấu nhất trên 37 ca hợp lệ (LLM/mẫu hỏi chuyển tiền trước — đúng câu mặc định của `fallback`) | Recall (73 ca lừa đảo) | Giá |
|---|---|---|---|
| Giữ nguyên (hiện tại) | **10/37 = 0,270 > 0,10 ⇒ Gate M3 trượt** khi có model thật; synthetic 0/37 chỉ vì thứ tự khóa cassette | 1,000 | 0 |
| **A (đề xuất). Câu hỏi nối tiếp tất định**: `transfer = yes` ⇒ sàn `high` + hỏi thêm đúng một câu `q_know_caller`; `no`/`unsure`/`timeout` ⇒ `critical`, `yes` ⇒ giữ `high` (LLM vẫn nâng được). Tối đa **2** câu/sự cố | **3/37 = 0,081** (`shipper_pay_wallet_002` "không biết người gọi"; `official_traffic_fine_004`, `utility_bill_notice_004` không có câu trả lời ⇒ `unsure`) — đạt nhưng sát ngưỡng (1 ca) | 1,000 trên synthetic (sàn của 73 ca đến từ luật máy, không từ câu trả lời); **rủi ro thật**: lừa đảo giả người thân mà người cao tuổi tin "biết người gọi" chỉ còn `high` (`call_now` thay `call_and_stay_on_line`) | E8 thêm 1 câu (≤ 60 s); đổi bất biến "tối đa 1 câu hỏi" của đồ thị (AGENTS.md) |
| B. Hạ sàn câu trả lời xuống `high`, để LLM quyết `critical` | dời báo nhầm sang LLM (model thật thấy cùng dữ kiện, có thể vẫn `critical`); `fallback` mất `critical` | 1,000 | rẻ nhưng chỉ chuyển chỗ vấn đề — **không đề xuất** |
| C. Đổi kỳ vọng `max_risk_level` của 10 ca thành `critical` | 0 trên giấy | — | **loại**: giấu báo nhầm (Hiến chương VII) |

- **(FR-012)** *(chỉ thi công khi Minh chọn A)*: `_ANSWER_FLOOR[("q_asked_transfer","yes")] = HIGH`; khi câu trả lời đó đến
  và chưa hỏi `q_know_caller`, `risk_scorer` đặt `question_id = "q_know_caller"` **tất định** (không theo LLM); sàn của câu
  thứ hai: `no`/`unsure`/`timeout` ⇒ `CRITICAL`, `yes` ⇒ không đổi. Không bao giờ quá 2 câu; câu thứ hai chỉ có trong nhánh này.
  `fallback` của `risk_scorer` theo cùng luật. Không đổi E8 Android (cùng màn, cùng ngân hàng câu hỏi), không đổi hợp đồng
  `elder_question/answer`.
- **(SC-008)** *(khi A)*: test ghim F-1 đảo chiều: 10 ca ép hỏi chuyển tiền ⇒ ≤ 3 ca `above_max_level`; eval full giữ recall
  1,000, báo nhầm ≤ 0,10, 0 vi phạm; 0 sự cố có > 2 câu hỏi (test riêng; `graph_loop` của eval giữ trần `MAX_ASK_ELDER = 3`).
