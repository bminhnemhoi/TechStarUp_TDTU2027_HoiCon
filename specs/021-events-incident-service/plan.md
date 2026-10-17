# Kế hoạch kỹ thuật: Spec 021 — Events & IncidentService

**Mã**: `specs/021-events-incident-service/plan.md` · **Làn B (Server)**

---

## 1. Kiến trúc CSDL & Bảng dữ liệu

### Bảng `incidents`
- `id`: UUID (Primary Key, UUIDv7)
- `family_id`: UUID (FK `families.id`, ondelete='CASCADE')
- `device_id`: UUID (FK `devices.id`, ondelete='SET NULL')
- `member_id`: UUID (FK `members.id`, ondelete='CASCADE')
- `status`: String(32) — Enum: `detected`, `assessing`, `awaiting_guardian`, `verifying`, `rescore`, `resolved_safe`, `resolved_prevented`, `resolved_false_alarm`, `resolved_no_response`, `case_open`, `closed`
- `level`: String(16) — Enum: `low`, `medium`, `high`, `critical`
- `rule_floor`: String(16) — Enum: `none`, `low`, `medium`, `high`, `critical`
- `version`: Integer (default 1) — phục vụ khóa lạc quan
- `is_drill`: Boolean (default False)
- `drill_id`: UUID | None
- `created_at`: DateTime (server_default=func.now())
- `updated_at`: DateTime (server_default=func.now(), onupdate=func.now())

### Bảng `incident_transitions`
- `id`: UUID (Primary Key, default new_id)
- `incident_id`: UUID (FK `incidents.id`, ondelete='CASCADE')
- `from_status`: String(32) | None
- `to_status`: String(32)
- `actor`: String(16) — Check: `system`, `guardian`, `elder`, `timer`
- `reason`: String(256) | None
- `metadata`: JSONB (server_default='{}'::jsonb)
- `transitioned_at`: DateTime (server_default=func.now())

### Bảng `risk_events`
- `id`: UUID (Primary Key, UUIDv7 do app gửi lên)
- `incident_id`: UUID | None (FK `incidents.id`, ondelete='SET NULL')
- `device_id`: UUID (FK `devices.id`, ondelete='CASCADE')
- `type`: String(32)
- `rule_id`: String(8) | None
- `rule_floor`: String(16)
- `occurred_at`: DateTime
- `caller_h1`: CHAR(64) | None
- `caller_last3`: CHAR(3) | None
- `app_category`: String(16) | None
- `app_package`: String(128) | None
- `timing_detect_ms`: Integer | None
- `timing_pause_ms`: Integer | None
- `is_drill`: Boolean (default False)
- `drill_id`: UUID | None
- `payload`: JSONB
- `received_at`: DateTime (server_default=func.now())

---

## 2. Dịch vụ `IncidentService`
- File: `backend/src/hoicon/services/incident_service.py`
- Các phương thức:
  - `create_incident(family_id, device_id, member_id, rule_floor, level, is_drill, drill_id, session) -> Incident`
  - `transition(incident_id, to_status, actor, reason, expected_version, session) -> Incident`
  - `correlate_event(event: RiskEvent, device: Device, session) -> Incident | None`
- Sử dụng `pg_advisory_xact_lock(hashtext(str(incident_id)))` để ngăn xung đột đa luồng/tiến trình.

---

## 3. Router `POST /v1/events`
- File: `backend/src/hoicon/api/routers/events.py`
- Xác thực: `Depends(get_current_device)`
- Nhận `EventsBatchRequest`: danh sách các `RiskEvent` (tối đa 50 sự kiện một đợt).
- Thực hiện lưu vào `risk_events` với `ON CONFLICT (id) DO NOTHING`.
- Đếm số bản ghi mới và số bản ghi trùng.
- Kiểm tra điều kiện mở sự cố qua `IncidentService.correlate_event`.
