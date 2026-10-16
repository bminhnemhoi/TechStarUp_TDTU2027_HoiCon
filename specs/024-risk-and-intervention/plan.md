# Kế hoạch Thực thi Spec 024: Đánh giá rủi ro, Ngân hàng câu hỏi E8 & Tác tử can thiệp

**Mã**: `024-risk-and-intervention` · **Tuần**: Phase 2 W3 · **Cột mốc**: Gate M1 / Gate M2

---

## 1. Kiến trúc & Thiết kế kỹ thuật

### 1.1 Luồng điều phối tổng thể

```
[Sự kiện gửi lên /v1/events]
           │
           ▼
[IncidentService.correlate_event] ───(Mở sự cố mới)───► [Khởi động IncidentRuntime.start]
                                                                   │
                                                                   ▼
                                                            [Node: ingest]
                                                                   │
                                                                   ▼
                                                          [Node: fast_alert]
                                                          (Gửi tin Zalo tức thời)
                                                                   │
                                                                   ▼
                                                         [Node: risk_scorer]
                                                                   │
                                               ┌───────────────────┴───────────────────┐
                                      (Cần hỏi E8)                           (Đủ thông tin)
                                               │                                       │
                                               ▼                                       │
                                     [Node: ask_elder]                                 │
                                   (Interrupt + Hẹn giờ 60s)                           │
                                               │                                       │
                                    (Gửi FCM / App polling)                            │
                                               │                                       │
                                     [Android: Màn hình E8]                            │
                                    (Người cao tuổi trả lời)                           │
                                               │                                       │
                                  [POST /v1/incidents/answers]                         │
                                               │                                       │
                                      (Resume đồ thị)                                  │
                                               │                                       │
                                               ▼                                       │
                                     [Node: risk_scorer]                               │
                                      (Đánh giá rủi ro lại)                            │
                                               │                                       │
                                               └───────────────────┬───────────────────┘
                                                                   │
                                                                   ▼
                                                        [Node: intervention]
                                                        (Tạo tóm tắt AI ≤ 15s)
                                                                   │
                                                        (Gửi tin chi tiết Zalo)
                                                                   │
                                                                   ▼
                                                       [Node: await_guardian]
                                                     (Interrupt + Timer T1/T2/T3)
                                                                   │
                                        ┌──────────────────────────┼──────────────────────────┐
                                   (Timer T1: 120s)           (Timer T2: 300s)           (Timer T3: 900s)
                                        │                          │                          │
                                   [Tin nhắc nhở]            [Leo thang rank 2]        [resolved_no_response]
                                        │                          │                          │
                                        └──────────────────────────┴──────────────────────────┘
                                                                   │
                                                      (Người giám hộ quyết định)
                                                                   │
                                                                   ▼
                                                           [Node: resolve]
                                                  (safe: resolved_safe,
                                                   scam: case_open,
                                                   no_response: resolved_no_response)
```

---

## 2. Các giai đoạn triển khai (Phases)

### Giai đoạn 1: Chuẩn bị Hợp đồng Schemas & Fixtures (Làn B)
- Định nghĩa JSON Schema: `docs/schemas/elder_question.v1.json` và `docs/schemas/elder_answer.v1.json`.
- Tạo các fixtures kiểm thử `valid` và `invalid` trong `docs/schemas/fixtures/`.
- Viết test hợp đồng Pydantic và test schema validation.

### Giai đoạn 2: Làn B - Backend API, Kênh FCM & Tác tử LangGraph
- Xây dựng module `hoicon.channels.fcm`: hỗ trợ push data message tới app Android (chế độ mock an toàn khi chưa cấu hình key production).
- Xây dựng Router `hoicon.api.routers.elder`:
  - `POST /v1/incidents/{id}/answers`: xác thực token thiết bị, gọi `IncidentRuntime.resume(expect="ask_elder")`.
  - `GET /v1/incidents/{id}/pending-question`: lấy câu hỏi đang chờ cho thiết bị.
- Nâng cấp `incident_graph.py` & `IncidentRuntime`:
  - Đồng bộ logic `risk_scorer` nâng level khi E8 trả lời `yes`.
  - Đảm bảo `intervention` áp dụng trần 4s LLM, tổng $\le 15\text{s}$, rơi về mẫu an toàn khi lỗi.
  - Sửa invariant tại `resolve`: scam chuyển sang `case_open` thay vì `resolved_prevented`.
  - Tích hợp tự động kích hoạt đồ thị khi `correlate_event` mở sự cố.
- Cấu hình Worker `hoicon.jobs.worker` xử lý timer T1/T2/T3 và E8 timeout.

### Giai đoạn 3: Làn A - Android Client & Màn hình Compose E8
- Tạo data models: `ElderQuestion`, `ElderAnswer`.
- Xây dựng `ElderApiClient` gọi API backend với xác thực token thiết bị.
- Thiết kế màn hình Compose E8 `ElderQuestionScreen.kt`:
  - 3 nút bấm kích thước lớn "Có", "Không", "Không rõ".
  - Nhãn công khai AI và nhãn diễn tập `[DIỄN TẬP]`.
  - Hỗ trợ giọng đọc TTS offline.
  - Đếm ngược thời gian 60s.
- Tích hợp `ElderQuestionActivity` vào luồng ứng dụng Sentinel.

### Giai đoạn 4: Kiểm chứng Tích hợp, E2E & Eval Smoke
- Viết integration test luồng E8 hoàn chỉnh từ sự kiện $\rightarrow$ câu hỏi E8 $\rightarrow$ trả lời E8 $\rightarrow$ can thiệp AI $\rightarrow$ timer T1/T2/T3.
- Chạy toàn bộ pytest, ruff check, gitleaks.
- Chạy `hoicon-eval smoke` kiểm chứng chất lượng đánh giá rủi ro.
- Chạy kiểm tra spec-trace `python3 scripts/check-spec-trace.py`.
