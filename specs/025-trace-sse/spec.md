# Spec 025: Luồng SSE Truy vết Tác tử (Agent Steps SSE Trace Stream)

**Mã ROADMAP**: `P2-10` · **Làn sở hữu**: Làn B (Server) · **Phụ thuộc**: `021-events-incident-service`, `024-risk-and-intervention` · **Cột mốc**: **Gate M2** · **Nhánh tính năng**: `feat/025-trace-sse`

---

## 1. Mục tiêu & Bối cảnh

Trong các đợt phát triển trước (Spec 021 & Spec 024), "bộ não" tác tử LangGraph (`IncidentRuntime`) đã được hoàn thiện. Mỗi node trong đồ thị khi thực thi (`ingest`, `fast_alert`, `risk_scorer`, `ask_elder`, `intervention`, `await_guardian`, `resolve`) đều tự động ghi lại một dòng vào bảng `agent_steps` trong cơ sở dữ liệu kèm theo số đo trễ (`latency_ms`), chi phí token (`cost_usd`), và nội dung đầu ra (`output`).

Tuy nhiên, bảng `agent_steps` hiện tại vẫn là một "hộp đen" nếu nhìn từ phía người dùng bên ngoài:
- Người giám hộ (qua giao diện Web ở Spec 027) hoặc kiểm toán viên không thể theo dõi thời gian thực tiến trình suy luận và đưa ra quyết định của tác tử.
- Các giao diện trực quan hóa dòng suy nghĩ (`/trace`, `/sim` ở Spec 033) chưa có kênh truyền dữ liệu dạng luồng đẩy (push stream).

Spec 025 giải quyết bài toán trên bằng cách xây dựng endpoint **Server-Sent Events (SSE)** tại `GET /v1/runs/{id}/stream` và endpoint lịch sử `GET /v1/runs/{id}/steps`. Toàn bộ dữ liệu đẩy ra stream phải được kiểm duyệt và che mờ PII 100% (`mask_text`), tuân thủ nghiêm ngặt Hiến chương dự án (ADR-006, ADR-009).

---

## 2. Tiêu chí thành công (Success Criteria)

- **(SC-001)**: **Độ trễ phát bước mới (SSE Latency)**: Khi một node trong đồ thị ghi dòng mới vào bảng `agent_steps`, sự kiện SSE tương ứng phải được phát tới client đang lắng nghe với độ trễ $p95 \le 500\text{ ms}$.
- **(SC-002)**: **Bảo vệ quyền riêng tư & Che mờ PII**: 100% dữ liệu xuất hiện trên luồng SSE (cả `output` lẫn `input_redacted`) không chứa số điện thoại thô (phải che dạng `[SĐT ***xxx]`), không chứa HMAC $h_1$ hay dữ liệu giọng nói/văn bản tự do (ADR-006, ADR-009).
- **(SC-003)**: **Heartbeat chống ngắt kết nối (Keep-Alive)**: Tự động gửi bình luận định kỳ `: ping\n\n` mỗi 15 giây khi không có bước mới, bảo đảm kết nối qua reverse proxy (Caddy / Nginx) không bị ngắt timeout.
- **(SC-004)**: **Truy vấn lịch sử đầy đủ**: Endpoint `GET /v1/runs/{id}/steps` trả về đầy đủ mảng JSON các bước đã thực hiện của run (sắp xếp tăng dần theo `at`), phục vụ nạp ban đầu cho client trước khi mở SSE stream.
- **(SC-005)**: **Đóng luồng tất định (Lifecycle Completion)**: Khi run đạt trạng thái kết thúc (`done` hoặc `failed`), stream phát sự kiện `event: done` với payload tóm tắt (`run_id`, `status`, `total_steps`, `cost_usd`) và chủ động đóng kết nối một cách an toàn.

---

## 3. Yêu cầu chức năng (Functional Requirements)

- **(FR-001)**: Ban hành JSON Schema hợp đồng `docs/schemas/agent_step_event.v1.json` và `docs/schemas/agent_steps_history.v1.json` kèm fixtures valid/invalid.
- **(FR-002)**: Xây dựng service `hoicon.services.trace_service`:
  - `get_run_steps(session, run_id)`: đọc danh sách các bước đã ghi của run.
  - `stream_run_steps(session_factory, run_id, last_step_id, poll_interval_s=0.5)`: async generator thăm dò và phát sinh các sự kiện SSE (`step`, `ping`, `done`).
- **(FR-003)**: Xây dựng router `hoicon.api.routers.runs`:
  - `GET /v1/runs/{id}/stream`: trả về `StreamingResponse` kiểu MIME `text/event-stream` với các header `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`.
  - `GET /v1/runs/{id}/steps`: trả về danh sách lịch sử các bước đã thực hiện.
- **(FR-004)**: Tích hợp tầng làm sạch dữ liệu (`Redaction Pipeline`): Áp dụng hàm `mask_text` đệ quy lên toàn bộ các trường text trong `output` và `input_redacted` trước khi serialize thành SSE payload.
- **(FR-005)**: Cơ chế ngắt kết nối an toàn (Graceful Disconnect): Bắt và xử lý `asyncio.CancelledError` khi client đóng kết nối, giải phóng toàn bộ tài nguyên DB session mà không gây rò rỉ kết nối trong connection pool.
- **(FR-006)**: Viết bộ test tích hợp toàn diện `backend/tests/integration/test_api_runs_sse.py`: kiểm tra luồng SSE (bước mới, ping, đóng luồng, che PII, 404 khi run không tồn tại) và test hợp đồng schemas.
