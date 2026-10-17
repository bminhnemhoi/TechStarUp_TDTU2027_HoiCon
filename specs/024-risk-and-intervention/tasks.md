# Danh sách Công việc Spec 024: Đánh giá rủi ro, Ngân hàng câu hỏi E8 & Tác tử can thiệp

- [x] T001 [FR-001] Định nghĩa JSON Schema hợp đồng `docs/schemas/elder_question.v1.json` và `docs/schemas/elder_answer.v1.json`.
- [x] T002 [FR-001] Tạo fixtures kiểm thử valid và invalid trong `docs/schemas/fixtures/` cho `elder_question` và `elder_answer`.
- [x] T003 [FR-002] Hiện thực kênh FCM client `hoicon.channels.fcm` với hỗ trợ dry-run/mock khi chưa có credentials production.
- [x] T004 [FR-003] Xây dựng router `hoicon.api.routers.elder` với endpoint `POST /v1/incidents/{id}/answers` xác thực token thiết bị.
- [x] T005 [FR-004] Xây dựng endpoint `GET /v1/incidents/{id}/pending-question` phục vụ cơ chế polling/fallback của thiết bị.
- [x] T006 [FR-005] Nâng cấp `incident_graph.py`: cập nhật `risk_scorer` theo câu trả lời E8, trần thời gian trong `intervention`, sửa invariant scam chuyển `case_open` tại `resolve`.
- [x] T007 [FR-006] Tích hợp tự động kích hoạt đồ thị LangGraph từ `POST /v1/events` khi sự cố mới được tạo hoặc nâng mức.
- [x] T008 [FR-007] Hoàn thiện xử lý job `graph_resume` cho timer T1 (120s nhắc), T2 (300s chuyển người giám hộ 2), T3 (900s dừng chờ) và timeout E8 trong worker.
- [x] T009 [FR-008] Thiết kế và triển khai màn hình Compose E8 `ElderQuestionScreen.kt` & `ElderQuestionActivity.kt` trên Android với 3 nút lớn, TTS offline, nhãn AI và diễn tập.
- [x] T010 [FR-009] Hiện thực `ElderApiClient` trên Android gửi câu trả lời `POST /v1/incidents/{id}/answers`; gửi qua `ElderAnswerWorker` (WorkManager, cần mạng, backoff, KEEP theo sự cố).
- [x] T011 [FR-010] Viết test hợp đồng schemas, test tích hợp API elder questions/answers và test đồ thị LangGraph với chuỗi hẹn giờ T1/T2/T3.
- [x] T012 [FR-010] Chạy toàn bộ testsuite pytest, ruff check, gitleaks, `hoicon-eval smoke` và cập nhật bằng chứng `evidence.md`.
- [ ] T013 [FR-002] Nối đường mở E8 trên máy: nhận FCM thật (chờ Firebase P0-08) hoặc tự kéo `pending-question` sau khi gửi sự kiện mở sự cố.
