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
