# Bằng chứng nghiệm thu: Spec 021 — Sự kiện rủi ro & Máy trạng thái sự cố (Events & IncidentService)

**Spec**: `specs/021-events-incident-service/spec.md` · **Mã ROADMAP**: P2-03 · **Làn B (server)** · **Nhánh**: `feat/021-events-incident-service` · **Ngày**: 16/10/2026
**Chưa commit/push.** Số đo lấy từ máy dev Linux + Postgres dev (cổng 15432); CI trên PR chưa chạy.

## Tiêu chí thành công (SC) ↔ số đo

| SC | Ngưỡng | Đo được | Đạt? | Bằng chứng |
|---|---|---|---|---|
| SC-001 | `POST /v1/events` lô 1–50, cần token thiết bị, idempotent 100% | Gửi lại cả lô: `accepted=0, duplicates=N`; 5 lô giống hệt gửi đồng thời ⇒ mỗi sự kiện đúng 1 dòng, đúng 1 sự cố; id lặp trong một lô và id của gia đình khác đều chỉ đếm là trùng | ✓ | `test_api_events.py` (41 test) |
| SC-002 | `transition()` nguyên tử, ghi `incident_transitions`, tăng `version`; xung đột bị từ chối | 10 bên cùng đọc version 1 ⇒ đúng 1 thắng, 9 nhận `ConcurrencyConflictError`, đúng 1 dòng nhật ký; giữ khóa advisory ở phiên khác ⇒ `transition` chờ | ✓ | `test_incident_service.py::test_concurrent_transitions_exactly_one_wins`, `test_transition_waits_for_the_advisory_lock` |
| SC-003 | `level >= rule_floor` bằng CHECK; trạng thái cuối không quay lại | Mọi cặp (level, rule_floor) = 20 ca INSERT + UPDATE hạ mức bị chặn; 121 cạnh (từ × đến) của máy trạng thái: chỉ cạnh trong `ALLOWED` qua, còn lại không ghi gì; trigger DB chặn rời/sửa sự cố đã kết thúc kể cả khi bỏ qua service | ✓ | `test_schema_0006.py`, `test_every_edge_of_the_state_machine` |
| SC-004 | Sự kiện `rule_floor ≥ high` hoặc loại kích hoạt mở sự cố ≤ 1 s; sự kiện sau liên kết vào sự cố đang mở | Mở sự cố trong cùng giao dịch với lô (đồng bộ, vài chục ms); 8 lô đồng thời cùng thiết bị ⇒ đúng 1 sự cố; thật và diễn tập, thiết bị khác nhau không lẫn; sàn cao hơn chỉ NÂNG `rule_floor` + `level` | ✓ | `test_incident_service.py`, `test_api_events.py` |
| SC-005 | 0 số điện thoại thô trong `risk_events`/`incidents` | Cột chỉ có `HMAC(pepper,h1)` + `last3`; `payload` đã bỏ `caller.h1`; dump cả hai bảng + log (`caplog` DEBUG) không chứa h1/HMAC/số; thân sai ⇒ 422 không lặp lại giá trị đã gửi; `repr()` không lộ h1 | ✓ | `test_only_the_hmac_and_last3_are_stored_never_h1`, `test_the_hash_never_appears_in_repr` |
| SC-006 | pytest ≥ 750, ruff sạch, eval smoke +0,0 %, spec-trace 0 lỗi | **961 passed**; `ruff check` + `ruff format --check` sạch; smoke: 20 ca, recall 100 %, báo nhầm 0 %, vi phạm 0, công khai AI 100 %, lệch baseline **+0,0 / +0,0 điểm %**; `check-spec-trace` 0 lỗi | ✓ | lệnh ở cuối |

## FR ↔ kiểm chứng

| FR | Kết quả |
|---|---|
| FR-001 migration `0006` | ✓ lên → xuống → lên trên DB dev và DB eval; `alembic check` chỉ lệch ở các bảng checkpoint của LangGraph (có từ trước); FK `action_tokens`/`messages_out` → `incidents` |
| FR-002 bất biến CSDL | ✓ CHECK `ck_incidents_level_ge_floor`, `closed_iff_terminal`; trigger `trg_incidents_terminal` (ALWAYS) |
| FR-003 schema | ✓ `events_batch`, `incident` + thêm `events_result` (phản hồi POST) và fixture valid/invalid; `test_events_batch_schema.py` |
| FR-004 `POST /v1/events` | ✓ DeviceAuth, `ON CONFLICT (id) DO NOTHING`, một lô = một giao dịch (lỗi giữa chừng ⇒ rollback, không mất sự kiện) |
| FR-005/006 `IncidentService` | ✓ `transition/create_incident/correlate_event`; advisory lock + `expected_version`; service không commit |
| FR-007 GET | ✓ `GET /v1/incidents/{id}`, `GET /v1/families/{id}/incidents` — nhà khác trả 404; `test_api_incidents.py` |
| FR-008 mở/liên kết | ✓ loại kích hoạt hoặc sàn ≥ high; cửa sổ liên kết 600 s tính từ hoạt động cuối |
| FR-009 PII | ✓ xem SC-005; `gitleaks` sạch ở `src`, `tests`, `migrations` |
| FR-010 tài liệu | ✓ `docs/API.md`, `docs/DATA-MODEL.md`. **`docs/ROADMAP.md` CHƯA cập nhật** (ngoài phạm vi lệnh giao của làn B) |

## Độ nhạy của test (đột biến, chạy tay rồi hoàn nguyên)
Bỏ khóa advisory · cho thoát trạng thái cuối · bỏ `ON CONFLICT DO NOTHING` · lưu h1 vào payload · bỏ lọc theo gia đình · hạ mức khi nâng · bỏ cửa sổ liên kết · bỏ rate limit · bỏ `lock_timeout` · bỏ lưới số điện thoại — **cả 11 đều làm test đỏ** (kể cả kiểm tổng chữ số). Lần đầu lưới số điện thoại sống sót (test chưa có ca đúng mẫu); đã thêm ca rồi bắt được.

## Review độc lập (`security-privacy-reviewer`, 2 lượt)
- **Lượt 1: 0 Critical, 2 High, 6 Medium, 8 Low.** Đã sửa: High #1 (không giới hạn tần suất + chờ khóa vô hạn giữ kết nối ⇒ rate limit 30 lô/phút/thiết bị + `lock_timeout` 3 s ⇒ 503), High #2 (sự cố bị bỏ quên nuốt mãi sự kiện ⇒ cửa sổ 600 s), Medium (chuỗi tự do `package/app_version/rules_version` lưu thô số điện thoại/OTP ⇒ pattern + lưới; số nguyên tràn int4 ⇒ 500 ⇒ cận trên; trigger chỉ-đọc cho sự cố đã kết thúc và nhật ký chuyển), Low (sắp id khi chèn, khóa thiết bị ở `create_incident`, `repr=False`, `StrictBool`, CHECK `caller_together`, xóa token mồ côi khi migrate).
- **Lượt 3 (đọc lại sửa của lượt 2): 0 Critical, 0 High, 1 Medium, 2 Low.** M1 còn lại: một số điện thoại chia đôi qua phần chính và hậu tố (`0912.3456-78`) và CCCD (`1234.5678-9012`) vẫn lọt ⇒ đã đổi sang giới hạn TỔNG chữ số ≤ 8 (chỉ ngoại lệ hậu tố ngày build `-20xxxxxx`), thêm 3 ca từ chối + 1 ca chấp nhận; đột biến bỏ kiểm tra này làm test đỏ. L1 `TRUNCATE`/quyền DDL không chặn được (ghi vào DATA-MODEL, prod thu quyền role ứng dụng); L2 loại mục cũ nhất của bảng giới hạn theo thứ tự chèn (chấp nhận ở quy mô thí điểm). **Các sửa của lượt 3 chưa có reviewer đọc lại.** `package` vẫn nhận đoạn chữ tùy ý (vd. `nguyen.van.a.tran`): chỉ allowlist `bank_apps` mới chặn hẳn.
- **Lượt 2 (đọc lại các sửa): 0 Critical, 0 High, 2 Medium, 5 Low.** M1 lưới số điện thoại bị vượt bằng hậu tố (`1.0-0912345678`) và M2 chặn nhầm `0.1.0-20261016` ⇒ đã thay bằng đếm chữ số theo thành phần (≤ 8) + test 7 phiên bản thật; L1 xóa trực tiếp `incident_transitions` ⇒ trigger chặn DELETE trực tiếp (CASCADE vẫn qua); L2 trần cứng bảng rate limit. Các sửa của lượt 2 đã được lượt 3 đọc lại.

## Chưa làm / cần Tiến quyết (không thuộc lệnh T001–T011)
- **#5** `drill_id` do thiết bị tự khai, chưa đối chiếu lịch diễn tập ⇒ một thiết bị có thể mở rất nhiều sự cố diễn tập (trần 30 lô × 50 sự kiện mỗi phút); cần bảng `drills` (P2-13) hoặc trần số sự cố diễn tập mở.
- **#6** `POST /v1/events` chưa kiểm sổ đồng ý (`call_screening`, `usage_monitoring`, `guardian_alerts`): rút đồng ý chưa có hiệu lực ở máy chủ.
- **#7** chưa có job `retention` (90 ngày `risk_events`, 12 tháng sự cố); chưa có xóa theo thiết bị.
- **#11/#12** khóa chống trùng là toàn cục theo `id` (id của gia đình khác ⇒ bị tính trùng); phạm vi đọc theo gia đình — ổn khi mỗi gia đình một thành viên được bảo vệ, cần xem lại khi nhiều thành viên.
- **L3** sự cố im lặng quá 600 s vẫn ở `detected` (một thiết bị có thể có nhiều sự cố mở) cho tới khi có bộ hẹn giờ `resolved_no_response` (spec tác tử).
- **Giới hạn thân yêu cầu** chưa có ở tầng ứng dụng (FastAPI đọc thân trước khi xác thực) ⇒ cần Caddy (`request_body max_size`) trước khi mở ra Internet. Hạn mức lô đếm trong bộ nhớ ⇒ chỉ đúng với một tiến trình (ADR-002).
- **Android (spec 022)** phải xử lý `429`/`503` + `Retry-After` bằng backoff và không bỏ sự kiện; outbox dồn nhiều lô khi vừa có mạng dễ chạm 30 lô/phút.
- **BLOCKED:** CI trên PR (chưa commit/push); chưa chạy trên Windows; p95 `POST /v1/events` chưa đo trên VPS (P1-09).

## Ghi chú vận hành
- Migration `0006` được **sửa tại chỗ** trong nhánh (chưa lên `main`). DB nào đã chạy bản `0006` cũ cần `alembic downgrade 0005 && alembic upgrade head` (mất dữ liệu 3 bảng mới, chấp nhận được ở dev). `0006` NULL hóa `messages_out.incident_id` và xóa `action_tokens` gắn sự cố cũ; downgrade không phục hồi.
- `ZaloWorld.new_incident()` trong test nay tạo sự cố THẬT (FK mới); `agents/spike.py` có `ensure_demo_incident` cho đường demo gửi tin tới gia đình.
- Hợp đồng `risk_event.v1.json` được **siết** (mẫu cho `package/app_version/rules_version`, cận trên số nguyên). Làn A cần giữ `versionName`/`rules_version` đúng mẫu `[tiền tố chữ][-_]?số≤4 chữ số(.số)*(-hoặc+hậu tố)`; ví dụ hợp lệ: `0.1.0`, `r1`, `rules-2026.12.01`, `0.1.0-20261016`.
- Handler 422 toàn cục nay không lặp lại giá trị đầu vào (áp cho mọi route).

## Lệnh đã chạy
```
uv run --directory backend ruff check . && uv run --directory backend ruff format --check .
uv run --directory backend alembic upgrade head && alembic downgrade -1 && alembic upgrade head   # dev + eval
uv run --directory backend pytest -q                                   # 961 passed
uv run --directory backend hoicon-eval --suite smoke --compare baseline  # ĐẠT, +0,0 / +0,0
python3 scripts/check-spec-trace.py
gitleaks detect --no-git --source backend/{src/hoicon,tests,migrations}  # no leaks found
```
