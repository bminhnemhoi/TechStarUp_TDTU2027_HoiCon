# Spec 021: Sự kiện rủi ro & Máy trạng thái sự cố (Events & IncidentService)

**Mã ROADMAP**: `P2-03` · **Làn sở hữu**: Làn B (Server) · **Phụ thuộc**: `020-family-pairing-consent` · **Nhánh tính năng**: `feat/021-events-incident-service`

---

## 1. Mục tiêu & Bối cảnh

Spec 021 hoàn thiện đường ống tiếp nhận sự kiện rủi ro từ app Lính gác (`POST /v1/events`), lưu trữ an toàn không rò rỉ PII thô (ADR-006), và vận hành máy trạng thái sự cố trung tâm (`IncidentService.transition()`) với cơ chế khóa lạc quan (optimistic locking) và PostgreSQL advisory lock chống xung đột giữa thao tác người giám hộ và bộ hẹn giờ hệ thống (DATA-MODEL §4).

---

## 2. Tiêu chí thành công (Success Criteria)

- **(SC-001)**: `POST /v1/events` tiếp nhận lô sự kiện (1–50 events) có kiểm tra token thiết bị `DeviceAuth`. Gửi lại cùng một lô (hoặc trùng event ID UUIDv7) tuyệt đối không tạo bản ghi trùng lặp (idempotent 100%).
- **(SC-002)**: Máy trạng thái `IncidentService.transition()` thực thi nguyên tử, ghi nhận vào bảng `incident_transitions`, tăng `version` sự cố; xung đột cập nhật đồng thời bị từ chối bằng lỗi 409 hoặc ngoại lệ `ConcurrencyConflictError`.
- **(SC-003)**: Bất biến CSDL: `incidents.level >= incidents.rule_floor` được bảo vệ bằng ràng buộc CHECK và kiểm thử đột biến. Các trạng thái kết thúc (`resolved_*`, `closed`) không cho phép quay ngược lại trạng thái trước.
- **(SC-004)**: Tự động khởi tạo sự cố khi nhận sự kiện có `rule_floor` $\in$ {`high`, `critical`} trong vòng $\le 1$ giây; liên kết tự động các sự kiện tiếp theo vào sự cố đang hoạt động của cùng thiết bị/gia đình.
- **(SC-005)**: Tuyệt đối 0 số điện thoại thô trong bảng `risk_events` và `incidents` (chỉ lưu `h1` và `last3`).
- **(SC-006)**: Cổng chất lượng: `pytest` backend toàn bộ xanh ($\ge 750$ passed), `ruff check` và `ruff format --check` sạch, `hoicon-eval --suite smoke --compare baseline` đạt +0.0%, `check-spec-trace.py` 0 lỗi.

---

## 3. Yêu cầu chức năng (Functional Requirements)

- **(FR-001)**: Migration Alembic `0006_events_incident_service.py` tạo các bảng `incidents`, `incident_transitions`, `risk_events` kèm theo các ràng buộc CHECK, chỉ mục và bổ sung khóa ngoại (Foreign Key) từ `action_tokens.incident_id`, `messages_out.incident_id` tới `incidents.id`.
- **(FR-002)**: Ràng buộc CSDL: `incidents.level >= incidents.rule_floor` (bất biến 1) và chặn chuyển trạng thái từ trạng thái cuối (`resolved_safe`, `resolved_prevented`, `resolved_false_alarm`, `resolved_no_response`, `closed`).
- **(FR-003)**: Hiện thực schemas `docs/schemas/events_batch.v1.json` và `docs/schemas/incident.v1.json` kèm fixtures kiểm thử valid/invalid.
- **(FR-004)**: Hiện thực endpoint `POST /v1/events`: yêu cầu `DeviceAuth` (Bearer token thiết bị từ Spec 020), nhận lô sự kiện theo `risk_event.v1.json`, lưu vào `risk_events` chống trùng lặp theo `id` (UUIDv7).
- **(FR-005)**: Hiện thực dịch vụ `IncidentService`: quản lý vòng đời sự cố (`detected` $\rightarrow$ `assessing` $\rightarrow$ `awaiting_guardian` $\rightarrow$ `verifying` / `rescore` $\rightarrow$ `resolved_*` / `closed`). Mọi chuyển trạng thái đều phải thông qua hàm `IncidentService.transition()`.
- **(FR-006)**: Hiện thực cơ chế khóa phân tán PostgreSQL `pg_advisory_xact_lock(incident_id)` và kiểm tra `expected_version` trong `IncidentService.transition()` chống race-condition.
- **(FR-007)**: Endpoint `GET /v1/incidents/{id}` và `GET /v1/families/{id}/incidents`: trả về chi tiết sự cố và danh sách sự cố của gia đình.
- **(FR-008)**: Tích hợp logic kích hoạt sự cố: khi nhận sự kiện có `type` $\in$ {`banking_app_foreground`, `flagged_number_call`, `sideload_detected`, `ask_child_pressed`} hoặc `rule_floor` $\ge$ `high` trong cửa sổ rủi ro thì tự động tạo sự cố `detected` nếu chưa có sự cố đang mở.
- **(FR-009)**: Ghi log truy vết và che PII: kiểm tra không có số điện thoại thô trong toàn bộ log xử lý sự kiện và sự cố.
- **(FR-010)**: Cập nhật tài liệu kỹ thuật trong `docs/API.md`, `docs/DATA-MODEL.md` và `docs/ROADMAP.md`.
