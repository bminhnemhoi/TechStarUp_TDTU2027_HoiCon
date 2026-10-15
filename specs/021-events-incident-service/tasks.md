---

description: "Tasks list — Spec 021 Events & IncidentService (HỏiCon Đợt 5 Làn B)"
---

# Tasks: Spec 021 — Sự kiện rủi ro & Máy trạng thái sự cố

**Input**: `specs/021-events-incident-service/{spec.md, plan.md}`, `docs/schemas/risk_event.v1.json`

**Chế độ chạy**: Tự hành một mạch (MASTER-PLAN §2.6).

**Phân làn sở hữu**: Làn B (Server) — `backend/**`, `docs/schemas/**`. Không đụng `apps/**`.

---

## Phase 1: Setup & Contract Schemas

- [x] T001 [B] Viết schema `docs/schemas/events_batch.v1.json` và `docs/schemas/incident.v1.json` kèm fixtures valid/invalid trong `docs/schemas/fixtures/` — FR-003 · Verify: `uv run --directory backend pytest tests/contract/test_events_batch_schema.py -v`
- [x] T002 [B] Viết test hợp đồng `backend/tests/contract/test_events_batch_schema.py` kiểm tra phân giải batch sự kiện và không có trường PII thô — FR-003, FR-009 · Verify: `uv run --directory backend pytest tests/contract/test_events_batch_schema.py -q`

---

## Phase 2: Foundational (Database & Migration 0006)

- [x] T003 [B] Viết test trước `backend/tests/integration/test_schema_0006.py`: kiểm tra bảng `incidents`, `incident_transitions`, `risk_events` đủ cột và ràng buộc; kiểm tra bất biến `level >= rule_floor`; kiểm tra không có cột số điện thoại thô; kiểm tra FK từ `action_tokens.incident_id` và `messages_out.incident_id` — FR-001, FR-002, FR-009, SC-003, SC-005 · Verify: `uv run --directory backend pytest tests/integration/test_schema_0006.py -q` (đỏ)
- [x] T004 [B] Viết migration Alembic `backend/migrations/versions/20261016_0006_events_incident_service.py` (revision 0006, down 0005) + khai báo Models SQLAlchemy trong `backend/src/hoicon/db/models.py` (`Incident`, `IncidentTransition`, `RiskEventRecord`) — FR-001, FR-002 · Verify: `uv run --directory backend alembic upgrade head && uv run --directory backend alembic downgrade -1 && uv run --directory backend alembic upgrade head && uv run --directory backend pytest tests/integration/test_schema_0006.py -q` (xanh)

---

## Phase 3: IncidentService & State Machine

- [x] T005 [B] Viết unit & integration test `backend/tests/integration/test_incident_service.py`: kiểm tra tạo sự cố, chuyển trạng thái qua `IncidentService.transition()`, ghi nhận `incident_transitions`, tăng `version`, chặn chuyển từ trạng thái kết thúc, và từ chối xung đột phiên bản (optimistic locking) — FR-005, FR-006, SC-002, SC-003 · Verify: `uv run --directory backend pytest tests/integration/test_incident_service.py -q` (đỏ)
- [x] T006 [B] Hiện thực `IncidentService` trong `backend/src/hoicon/services/incident_service.py`: hỗ trợ chuyển trạng thái nguyên tử, áp dụng `pg_advisory_xact_lock` và xử lý ngoại lệ `ConcurrencyConflictError` — FR-005, FR-006, SC-002 · Verify: `uv run --directory backend pytest tests/integration/test_incident_service.py -q` (xanh)

---

## Phase 4: Endpoint Tiếp nhận Sự kiện (POST /v1/events)

- [x] T007 [B] Viết test trước `backend/tests/integration/test_api_events.py`: gọi `POST /v1/events` không có token $\rightarrow$ 401; gửi lô sự kiện hợp lệ $\rightarrow$ 200; gửi lại sự kiện đã có ID $\rightarrow$ trả 200 và đếm `duplicates` (idempotent); gửi sự kiện có `rule_floor=high` $\rightarrow$ tự động mở sự cố mới — FR-004, FR-008, SC-001, SC-004 · Verify: `uv run --directory backend pytest tests/integration/test_api_events.py -q` (đỏ)
- [x] T008 [B] Hiện thực router `POST /v1/events` trong `backend/src/hoicon/api/routers/events.py`: nhận lô sự kiện, chèn với cơ chế `ON CONFLICT DO NOTHING`, kích hoạt `IncidentService.correlate_event()` — FR-004, FR-008, SC-001, SC-004 · Verify: `uv run --directory backend pytest tests/integration/test_api_events.py -q` (xanh)
- [x] T009 [B] Hiện thực endpoint `GET /v1/incidents/{id}` và `GET /v1/families/{id}/incidents` trong `backend/src/hoicon/api/routers/incidents.py` — FR-007 · Verify: `uv run --directory backend pytest tests/integration/test_api_incidents.py -q`

---

## Phase 5: Verification & Documentation

- [x] T010 [B] Kiểm tra log bảo mật không chứa số điện thoại thô hoặc PII và hoàn thiện tài liệu trong `docs/API.md`, `docs/DATA-MODEL.md` — FR-009, FR-010, SC-005 · Verify: review & test
- [x] T011 [B] Cổng chất lượng Làn B: `ruff check` + `ruff format --check` sạch, `pytest` toàn bộ $\ge 750$ passed, `hoicon-eval --suite smoke --compare baseline` đạt +0.0% — SC-006 · Verify: `cd backend && uv run ruff check . && uv run pytest -q`
