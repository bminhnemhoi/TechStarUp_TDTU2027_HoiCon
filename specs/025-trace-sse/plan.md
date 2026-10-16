# Kế hoạch Thực thi Spec 025: Luồng SSE Truy vết Tác tử (Agent Steps SSE Trace Stream)

**Mã**: `025-trace-sse` · **Tuần**: Phase 2 W3 · **Cột mốc**: Gate M2

---

## 1. Kiến trúc & Thiết kế kỹ thuật

### 1.1 Luồng truyền dữ liệu Server-Sent Events (SSE)

```
[Client / Web Browser / Monitor]
           │
           │  GET /v1/runs/{id}/stream (Accept: text/event-stream)
           ▼
[FastAPI Router: /v1/runs/{id}/stream]
           │
           │  Mở async generator stream_run_steps(session_factory, run_id)
           ▼
[TraceService Loop (mỗi 0.5s)]
           │
           ├────► [Truy vấn agent_steps WHERE run_id = :id AND at > :last_at]
           │             │
           │             ▼ (Có bước mới)
           │      [Làm sạch & Che mờ PII qua mask_text]
           │             │
           │             ▼
           │      Yield: "event: step\ndata: { ... }\n\n"
           │
           ├────► [Kiểm tra thời gian trôi qua ≥ 15s mà không có bước mới]
           │             │
           │             ▼
           │      Yield: ": ping\n\n"
           │
           └────► [Truy vấn agent_runs WHERE id = :id]
                         │
                         ▼ (status IN ('done', 'failed'))
                  Yield: "event: done\ndata: { ... }\n\n"
                  [Kết thúc Generator & Đóng kết nối an toàn]
```

### 1.2 Định dạng giao thức SSE chuẩn

1. **Sự kiện bước chạy mới (`event: step`)**:
   ```
   event: step
   id: 0192e2b0-8c29-79f8-b3d1-92b0c478a221
   data: {"id":"0192e2b0-8c29-79f8-b3d1-92b0c478a221","run_id":"0192e2b0-8c10-72a1-a029-7b3c4f92d831","node":"fast_alert","model_profile":null,"latency_ms":12,"tokens_in":0,"tokens_out":0,"cost_usd":"0.000000","output":{"template":"fast_alert"},"at":"2026-10-16T08:30:00Z"}
   ```

2. **Dòng giữ kết nối (`heartbeat ping`)**:
   ```
   : ping
   ```

3. **Sự kiện kết thúc chạy (`event: done`)**:
   ```
   event: done
   data: {"run_id":"0192e2b0-8c10-72a1-a029-7b3c4f92d831","status":"done","total_steps":6,"cost_usd":"0.002450"}
   ```

### 1.3 Quản trị tài nguyên & Chống rò rỉ Connection Pool
- Mỗi vòng lặp thăm dò (polling loop) trong generator sử dụng context manager `async with session_factory() as session` ngắn gọn rồi giải phóng kết nối ngay về pool, **không giữ mở transaction kéo dài suốt thời gian stream**.
- Bắt ngoại lệ `asyncio.CancelledError` khi client ngắt kết nối (đóng tab, mất mạng) để thoát vòng lặp ngay lập tức và ghi log debug.

---

## 2. Các giai đoạn triển khai (Phases)

### Giai đoạn 1: Chuẩn bị Hợp đồng Schemas & Fixtures (Làn B)
- Định nghĩa JSON Schema: `docs/schemas/agent_step_event.v1.json` và `docs/schemas/agent_steps_history.v1.json`.
- Tạo fixtures kiểm thử valid/invalid trong `docs/schemas/fixtures/`.
- Viết test hợp đồng schemas kiểm tra tính hợp lệ.

### Giai đoạn 2: Tầng Dịch vụ & Làm sạch Dữ liệu (TraceService & Redaction)
- Xây dựng `hoicon.services.trace_service`:
  - `get_run_steps(session, run_id)`: đọc lịch sử các bước đã thực hiện.
  - `stream_run_steps(session_factory, run_id, last_step_id, poll_interval_s=0.5)`: async generator phát sự kiện SSE.
- Tích hợp đệ quy `mask_text` cho mọi chuỗi văn bản trong JSON object để che số điện thoại thô.

### Giai đoạn 3: Tầng API Router (FastAPI Streaming)
- Xây dựng router `hoicon.api.routers.runs`:
  - `GET /v1/runs/{id}/stream`: trả về `StreamingResponse` kiểu `text/event-stream`.
  - `GET /v1/runs/{id}/steps`: trả về danh sách lịch sử JSON.
- Đăng ký router `runs.router` vào `hoicon.api.main.py`.
- Cấu hình các headers `Cache-Control: no-cache`, `X-Accel-Buffering: no` (cho Caddy/Nginx).

### Giai đoạn 4: Kiểm chứng Tích hợp & Nghiệm thu
- Viết test tích hợp `backend/tests/integration/test_api_runs_sse.py`:
  - Test nạp lịch sử steps.
  - Test stream bước chạy với giả lập agent ghi vào DB.
  - Test phát ping định kỳ và phát event done.
  - Test 404 khi run không tồn tại.
  - Test ngắt kết nối client an toàn không crash server.
- Chạy toàn bộ pytest, ruff check, gitleaks, `check-spec-trace.py`.
