# Danh sách Công việc Spec 025: Luồng SSE Truy vết Tác tử (Agent Steps SSE Trace Stream)

- [ ] T001 [FR-001] Định nghĩa JSON Schema hợp đồng `docs/schemas/agent_step_event.v1.json` và `docs/schemas/agent_steps_history.v1.json`.
- [ ] T002 [FR-001] Tạo fixtures kiểm thử valid và invalid trong `docs/schemas/fixtures/` cho `agent_step_event` và `agent_steps_history`.
- [ ] T003 [FR-002] Hiện thực `AgentStepService.get_run_steps` truy vấn lịch sử các bước đã ghi của run theo thứ tự thời gian.
- [ ] T004 [FR-004] Tích hợp bộ lọc che mờ PII đệ quy (`mask_text`) áp dụng trên mọi trường dữ liệu của step trước khi phát ra bên ngoài.
- [ ] T005 [FR-002] [FR-005] Xây dựng async generator `stream_run_steps` trong `trace_service`: thăm dò bước mới, phát `: ping` mỗi 15s, phát `event: done` và xử lý hủy kết nối an toàn.
- [ ] T006 [FR-003] [FR-005] Xây dựng router `hoicon.api.routers.runs` với endpoint `GET /v1/runs/{id}/stream` (FastAPI `StreamingResponse`) và `GET /v1/runs/{id}/steps`.
- [ ] T007 [FR-003] Đăng ký router `runs.router` vào `hoicon.api.main.py` và cập nhật tài liệu `docs/API.md`.
- [ ] T008 [FR-006] Viết bộ test hợp đồng schemas và test tích hợp `backend/tests/integration/test_api_runs_sse.py` kiểm chứng đầy đủ luồng SSE, ping, done và che PII.
- [ ] T009 [FR-006] Chạy toàn bộ testsuite pytest, ruff check, gitleaks, cập nhật bằng chứng nghiệm thu `evidence.md` và xác nhận spec-trace.
