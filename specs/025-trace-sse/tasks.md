# Công việc Spec 025: Luồng SSE truy vết tác tử

Chạy một mạch từ T001 tới T014. Không có task nào chờ duyệt tay. Mỗi task phải chạy lệnh `Verify` của nó và thấy xanh rồi
mới sang task kế tiếp. Lệnh `uv run` chạy từ thư mục gốc repo, kèm `--directory backend`.

## Giai đoạn 1: Hợp đồng
- [x] T001 [FR-001] Viết `docs/schemas/agent_step.v1.json`, `run_steps.v1.json` và `run_done.v1.json` (draft 2020-12,
  `additionalProperties: false`, `cost_usd` là chuỗi `^\d+\.\d{6}$`, `node` theo `^[a-z_]{1,64}$`, `status` thuộc enum
  của `agent_runs`). Viết fixture `valid` và `invalid` trong `docs/schemas/fixtures/`. Fixture invalid phải có trường
  `input_redacted`, khóa `h1` trong `output` và `cost_usd` dạng số, và schema phải bắt được cả ba lỗi đó.
  · Verify: `uv run --directory backend pytest tests/contract/test_trace_schemas.py`
- [x] T002 [FR-001] [FR-009] Viết `backend/tests/contract/test_trace_schemas.py`. Test kiểm fixture valid qua, fixture
  invalid trượt, và kiểm `step_view` (T005) dựng ra đúng schema.
  · Verify: như T001

## Giai đoạn 2: Che dữ liệu
- [x] T003 [FR-002] Thêm `TRACE_DENY_KEYS` và `redact_json` vào `backend/src/hoicon/domain/pii.py` theo quy tắc ở
  plan §5.
  · Verify: `uv run --directory backend pytest tests/unit/test_redact_json.py`
- [x] T004 [FR-002] [FR-009] Viết `backend/tests/unit/test_redact_json.py` với các ca:
  - khóa cấm ở độ sâu 3;
  - hex 64 ký tự ⇒ `[HASH]`;
  - token 43 ký tự ⇒ `[TOKEN]`;
  - số di động hư cấu ⇒ `[SĐT ***xxx]`;
  - `"20.000.000 đồng"` giữ nguyên;
  - chuỗi 2.000 ký tự cắt còn 500;
  - tính lũy đẳng;
  - `None`, số và bool giữ nguyên.

  · Verify: như T003

## Giai đoạn 3: Dịch vụ
- [x] T005 [FR-003] Viết `backend/src/hoicon/services/trace_service.py` gồm `step_view` (danh sách trắng cột, `output`
  đi qua `redact_json`), `list_steps(session, run_id, after, limit=500)` dùng khóa `(at, id)` qua `tuple_`, và
  `run_done_view`.
  · Verify: `uv run --directory backend pytest tests/unit/test_trace_stream.py tests/contract/test_trace_schemas.py`
- [x] T006 [FR-004] [FR-005] Viết `stream_run(...)`, các hằng `POLL_S=0.3`, `PING_S=15`, `MAX_STREAM_S=600`,
  `DB_FAIL_LIMIT=3`, bộ đếm chỗ (`MAX_STREAMS=20`, `MAX_STREAMS_PER_MEMBER=3`) và `TraceStreamResponse` (`finally`:
  `aclose()` rồi nhả chỗ). Mỗi nhịp đọc trạng thái trước, đọc bước sau, và đóng session trước khi `yield`. Không nuốt
  `CancelledError`/`GeneratorExit`.
  · Verify: như T005
- [x] T007 [FR-004] [FR-005] [FR-009] Viết `backend/tests/unit/test_trace_stream.py`, dùng session giả và hằng số thu
  nhỏ:
  - khung đầu là `retry: 3000`;
  - có `: ping` sau `PING_S`;
  - `done` đến sau bước cuối, đúng một lần;
  - lượt `waiting` không đóng;
  - quá `MAX_STREAM_S` thì đóng;
  - `Last-Event-ID` lạ thì phát lại từ đầu;
  - hai bước cùng `at` không mất bước nào;
  - 3 lỗi DB thì phát `event: error` rồi đóng;
  - `aclose()` giữa chừng thì không còn session nào mở.

  · Verify: như T005

## Giai đoạn 4: API
- [x] T008 [FR-006] Viết `backend/src/hoicon/api/routers/runs.py` với `GET /v1/runs/{run_id}/steps` và
  `GET /v1/runs/{run_id}/stream`.
  - Quyền xem: `get_current_guardian` → lượt → `thread_id` parse thành UUID → `Incident.family_id == claims.family_id`.
    Sai ở bất kỳ bước nào ⇒ 404.
  - Mã 429/503 (kèm `Retry-After`) trả trước khi stream bắt đầu.
  - Header: `Cache-Control: no-cache`, `X-Accel-Buffering: no`. Không có `Connection`.
  - Đọc `Last-Event-ID` từ header, không nhận token qua query.

  · Verify: `uv run --directory backend pytest tests/integration/test_api_runs.py`
- [x] T009 [FR-007] Thêm `GET /v1/incidents/{incident_id}/run` (JWT người giám hộ, cùng gia đình) trả
  `{"run_id", "status"}`. Chưa có lượt hoặc khác gia đình ⇒ 404.
  · Verify: như T008
- [x] T010 [FR-008] Gắn `runs.router` vào `backend/src/hoicon/api/main.py`. Khai báo OpenAPI cho route stream là
  `text/event-stream`. Chạy `bash scripts/gen-api-client.sh`, rồi `pnpm --dir apps/web typecheck` phải xanh. Viết lại
  mục "Luồng SSE" trong `docs/API.md`: khung, header, mã lỗi, `Last-Event-ID`, và lưu ý client dùng `fetch`, không dùng
  `EventSource`.
  · Verify: `bash scripts/gen-api-client.sh && pnpm --dir apps/web typecheck`

## Giai đoạn 5: Tích hợp
- [x] T011 [FR-006] [FR-007] [FR-009] Viết `backend/tests/integration/test_api_runs.py`, chạy qua ASGITransport. Mọi lượt
  dùng trong file này phải đã kết thúc. Các ca:
  - `/steps` khớp DB theo `(at, id)` và giống hệt payload SSE;
  - luồng của lượt `done` kết thúc bằng `event: done` có số đếm và chi phí khớp DB;
  - bước "đầu độc" (SC-002) ra 0 SĐT thô, 0 hex ≥ 32, 0 khóa cấm, không có `input_redacted`;
  - 401 khi không có token;
  - 404 cho gia đình khác, lượt `eval-…` và id lạ;
  - 429 ở luồng thứ 4 của cùng một người, 503 khi vượt `MAX_STREAMS`;
  - `/v1/incidents/{id}/run`.

  Dọn dữ liệu bằng `purge_family`.
  · Verify: như T008
- [x] T012 [FR-005] [FR-009] Viết `backend/tests/integration/test_trace_sse_live.py`, chạy trên uvicorn thật qua
  `uvicorn.Server`, cổng 0, task nền, client `httpx.AsyncClient.stream`. Các ca:
  - bước chèn trong lúc stream thì tới client;
  - `: ping` xuất hiện với `PING_S` thu nhỏ;
  - ngắt đột ngột 50 lần, sau đó `get_engine().pool.checkedout()` và bộ đếm chỗ về mức ban đầu;
  - nối lại với `Last-Event-ID` không nhận trùng bước;
  - đo SC-001: n = 30, in p50/p95. Ngưỡng assert là p95 ≤ 1 s (để CI ổn định). Số thật ghi vào evidence.

  · Verify: `uv run --directory backend pytest tests/integration/test_trace_sse_live.py -s`

## Giai đoạn 6: Nghiệm thu
- [x] T013 [FR-010] Chạy đủ bộ lệnh kiểm:
  - `uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache`;
  - `ruff check` và `ruff format --check` (`--cache-dir /tmp/ruff_cache src/ tests/`);
  - gitleaks **từng thư mục**: `backend/src`, `backend/tests`, `docs/schemas`, `specs/025-trace-sse`;
  - `hoicon-eval --suite smoke --compare baseline … --shared-db-ok` (chạy làm hồi quy);
  - `python3 scripts/check-spec-trace.py`;
  - `git diff --stat -- backend/src/hoicon/agents backend/src/hoicon/prompts backend/src/hoicon/jobs` phải rỗng.

  · Verify: tất cả các lệnh trên xanh
- [x] T014 [FR-010] Điền `evidence.md` bằng số đo thật, ghi rõ nguồn: máy dev, localhost, ngày. Thêm vào ROADMAP
  "Ghi chú" mục `agent_runs.incident_id` chưa được ghi. Giữ `P2-10` ở ◐ cho tới khi 027/033 tiêu thụ luồng.
  · Verify: `python3 scripts/check-spec-trace.py` ⇒ 0 lỗi
