# Kế hoạch Spec 025: Luồng SSE truy vết tác tử

**Mã**: `025-trace-sse` · **ROADMAP**: `P2-10` · **Làn**: B · **Cột mốc**: Gate M2 · Spec: [`spec.md`](spec.md)

## 1. Kiểm theo hiến chương (`.specify/memory/constitution.md`)

| Nguyên tắc | Áp dụng ở spec này |
|---|---|
| I. Dừng an toàn tất định | Không đụng: luồng chỉ đọc, chạy ngoài đường dừng an toàn |
| II. Riêng tư theo thiết kế | Hai lớp độc lập: danh sách trắng cột (`step_view`) + `redact_json` (FR-002/003); bỏ `input_redacted`; cấm token trong URL |
| III. LLM chỉ nâng, qua `llm_router` | Không gọi LLM; không sửa `agents/**` |
| IV. Công khai AI + đồng ý | Không có tin mới tới người cao tuổi; không có mục đích dữ liệu mới (dữ liệu sự cố đã có đồng ý ở 020) |
| V. Hợp đồng trước | `agent_step.v1`, `run_steps.v1`, `run_done.v1` + fixture viết TRƯỚC code; sinh lại client TS |
| VI. UX người cao tuổi | Không có màn hình (027/033 làm giao diện) |
| VII. Bằng chứng trung thực | SC-001 đo trên localhost; phần qua Caddy ghi CHƯA ĐO tới khi có 012 |
| VIII. Ít code, tái sử dụng | Không thêm thư viện SSE; dùng `get_current_guardian`, `get_sessionmaker`, `mask_text`, chỉ mục sẵn có |
| IX. Chặn phát hành | Không đổi |

**Tái sử dụng (bắt buộc trước khi viết mới):**
- `hoicon.domain.pii.mask_text`;
- `hoicon.api.auth.get_current_guardian` / `GuardianClaims`;
- `hoicon.db.session.get_sessionmaker`;
- `AgentRun`, `AgentStep`, `Incident` (`db/models.py`);
- mẫu test `consent_support.purge_family` và fixture JWT người giám hộ trong `tests/integration/test_guardian_alert.py`;
- `scripts/gen-api-client.sh`.

## 2. Luồng dữ liệu

```
Node đồ thị ──step()──► INSERT agent_steps (giao dịch riêng, commit)        IncidentRuntime._set_status ──► agent_runs.status
                                   │                                                             │
GET /v1/runs/{id}/stream ──► [kiểm trước khi stream] JWT người giám hộ → run → thread_id→incident.family_id
   (fetch + Authorization,        │  401 / 404 / 429 (≥3 luồng/người) / 503 (≥20 luồng/tiến trình)
    Last-Event-ID khi nối lại)    ▼
                    TraceStreamResponse(stream_run(...))            ◄── finally: aclose() + nhả chỗ bộ đếm
                                   │
             ┌──── mỗi nhịp POLL_S = 0,3 s ───────────────────────────────────────────────┐
             │ async with sessions() as s:          ← mượn 1 kết nối, KHÔNG giữ qua yield   │
             │     status = SELECT status FROM agent_runs WHERE id=:run      (1) trước     │
             │     rows   = SELECT … FROM agent_steps WHERE run_id=:run                    │
             │              AND (at, id) > (:at, :id) ORDER BY at, id LIMIT 100   (2) sau  │
             │ (session đóng ⇒ rollback, kết nối về pool)                                  │
             │ rows      ⇒ yield "id/event: step/data" từng dòng, cập nhật con trỏ (at, id) │
             │ không rows và status ∈ {done, failed} ⇒ yield "event: done" ⇒ thoát          │
             │ ≥ PING_S kể từ lần ghi cuối ⇒ yield ": ping"                                │
             │ ≥ MAX_STREAM_S ⇒ thoát (client nối lại bằng Last-Event-ID)                  │
             │ await request.is_disconnected() ⇒ thoát                                     │
             └─────────────────────────────────────────────────────────────────────────────┘
```

**Vì sao đọc trạng thái trước, bước sau.** `resolve` commit dòng bước rồi `_set_status("done")` mới commit. Đọc trạng
thái trước (READ COMMITTED) thì câu đọc bước chạy sau sẽ thấy mọi bước đã commit trước khi trạng thái đổi. Nhờ vậy
`done` không bao giờ đến trước bước cuối.

**Vì sao con trỏ là `(at, id)`.** `at = now()` là giờ bắt đầu giao dịch. Các bước của một lượt được ghi tuần tự, vì
`IncidentRuntime` khóa theo thread, nên `at` tăng dần. `id` (UUIDv7) phân xử khi trùng `at`. Truy vấn đi theo chỉ mục
`ix_agent_steps_run_at`. Có test chèn hai bước cùng `at` để chắc không mất bước nào.

**Vì sao `POLL_S = 0,3 s`, không phải 0,5 s.** Với thăm dò chu kỳ T, độ trễ gần như phân bố đều trên [0, T] + thời gian
truy vấn. T = 0,5 cho p95 ≈ 0,475 s + truy vấn: sát trần 500 ms, test dễ chập chờn. T = 0,3 cho p95 ≈ 0,29 s + truy vấn.
Tải DB với 20 luồng ≈ 133 truy vấn chỉ mục/giây, mỗi lần mượn kết nối vài ms. Pool 5 + 10 dư sức, kể cả khi chạy chung
worker.

## 3. Giao thức SSE

Mã hóa UTF-8. `data` là JSON một dòng (`json.dumps(..., ensure_ascii=False, separators=(",", ":"))`). Mỗi khung kết thúc
bằng một dòng trống.

```
retry: 3000

id: 0192e2b0-8c29-79f8-b3d1-92b0c478a221
event: step
data: {"id":"0192e2b0-8c29-79f8-b3d1-92b0c478a221","run_id":"0192e2b0-8c10-72a1-a029-7b3c4f92d831","node":"risk_scorer","model_profile":"fast","model":null,"prompt_version":"risk_scorer@3","latency_ms":412,"tokens_in":0,"tokens_out":0,"cost_usd":"0.000000","fallback_used":true,"error":"timeout","output":{"level":"high","tactic":"authority","question":"q_caller_authority","llm_level":null},"at":"2026-10-16T08:30:00.123456Z"}

: ping

event: done
data: {"run_id":"0192e2b0-8c10-72a1-a029-7b3c4f92d831","status":"done","total_steps":7,"cost_usd":"0.002450","is_drill":false,"is_demo":false}

event: error
data: {"retryable":true}
```

- `id:` chỉ có ở `event: step`, nên trình duyệt hoặc client gửi lại đúng `Last-Event-ID` của bước cuối đã nhận.
- `cost_usd` là chuỗi thập phân 6 chữ số, không dùng float.
- `output` có thể là `null` (job `retention` xóa nội dung sau 30 ngày, DATA-MODEL §6).
- Trường `step` được xuất theo danh sách trắng: `id, run_id, node, model_profile, model, prompt_version, latency_ms,
  tokens_in, tokens_out, cost_usd, fallback_used, error, output, at`. Không có `input_redacted`.

`run_steps.v1`: `{"run_id", "status", "is_drill", "is_demo", "steps": [agent_step…]}` (tối đa 500 bước; lượt sự cố thật
có khoảng 7–15 bước).

**Hằng số** (đặt ở module `trace_service`, test monkeypatch như `runtime_service.SHUTDOWN_WAIT_S`):

| Hằng | Giá trị | Lý do |
|---|---|---|
| `POLL_S` | 0,3 | SC-001 (§2) |
| `PING_S` | 15 | SC-003; dưới hạn chờ đọc mặc định của proxy (Caddy không cắt, nginx 60 s) |
| `MAX_STREAM_S` | 600 | Lượt `waiting` có thể kéo dài tới T3 (900 s); đóng định kỳ để nhả chỗ, client nối lại |
| `MAX_STREAMS` / `MAX_STREAMS_PER_MEMBER` | 20 / 3 | Bộ đếm trong bộ nhớ, đúng với một tiến trình (ADR-002) |
| `DB_FAIL_LIMIT` | 3 | Ba nhịp lỗi liên tiếp ⇒ `event: error` rồi đóng |

## 4. Ngắt kết nối & giải phóng tài nguyên

1. **Không giữ gì qua `yield`.** Session mở và đóng trọn trong một nhịp. Khi client biến mất giữa chừng, thứ duy nhất còn
   treo là generator đang đứng ở `yield`, và nó không giữ kết nối DB.
2. **Starlette 1.7 có hai đường báo ngắt:**
   - ASGI < 2.4: task nghe `http.disconnect` hủy task group, generator nhận `CancelledError`.
   - ASGI ≥ 2.4: `send` ném `OSError` ⇒ `ClientDisconnect`, generator **không** tự được đóng, chỉ bị GC dọn sau.

   `TraceStreamResponse.__call__` bọc `try: await super().__call__(…) finally: await self.body_iterator.aclose();
   release_slot()` để dọn tất định trong cả hai trường hợp.
3. **Không nuốt `CancelledError`/`GeneratorExit`:** chỉ `finally` (log debug `run_id` + số bước đã phát), không `except` rồi
   `return`.
4. **Ngắt khi đang im lặng:** `await request.is_disconnected()` mỗi nhịp ⇒ thoát trong ≤ 0,3 s, không phải đợi tới lần
   ghi `: ping` kế tiếp mới phát hiện.
5. **Lỗi DB** (`SQLAlchemyError`, `OSError`, `TimeoutError`): bỏ qua nhịp đó, đếm số lần liên tiếp, tới `DB_FAIL_LIMIT` ⇒
   `event: error` rồi đóng. Log chỉ ghi tên lớp ngoại lệ, giống `runtime_service._worker_loop`.

## 5. Bản đồ file

| File | Thay đổi |
|---|---|
| `docs/schemas/agent_step.v1.json`, `run_steps.v1.json`, `run_done.v1.json` + `fixtures/*.{valid,invalid}.json` | mới |
| `backend/src/hoicon/domain/pii.py` | thêm `TRACE_DENY_KEYS`, `redact_json` |
| `backend/src/hoicon/services/trace_service.py` | mới: `step_view`, `list_steps`, `run_done_view`, `stream_run`, `TraceStreamResponse`, bộ đếm chỗ |
| `backend/src/hoicon/api/routers/runs.py` | mới: `/v1/runs/{id}/steps`, `/v1/runs/{id}/stream`, `/v1/incidents/{id}/run` |
| `backend/src/hoicon/api/main.py` | `include_router(runs.router)` |
| `backend/tests/unit/test_redact_json.py`, `test_trace_stream.py` | mới |
| `backend/tests/contract/test_trace_schemas.py` | mới |
| `backend/tests/integration/test_api_runs.py` (ASGITransport), `test_trace_sse_live.py` (uvicorn thật) | mới |
| `apps/web/src/lib/api/openapi.json`, `schema.d.ts` | sinh lại |
| `docs/API.md` (mục Luồng SSE), `docs/ROADMAP.md` (P2-10 + Ghi chú `agent_runs.incident_id`) | cập nhật |

`TRACE_DENY_KEYS = {"h1", "hmac", "phone", "phone_hmac", "last3", "package", "caller", "token", "action_token", "chat_id",
"zalo_user_id", "note", "text", "input_redacted"}`. `text` bị cấm vì đó là thân tin Zalo trong payload job. Bước hiện nay
không có khóa này; cấm sẵn để phòng node sau này lỡ ghi nó vào.

## 6. Giai đoạn

1. **Hợp đồng:** 3 schema + fixture + `test_trace_schemas.py` (đỏ trước, xanh sau).
2. **Che dữ liệu:** `redact_json` + test unit (khóa lồng sâu, hex 64, token 43, số điện thoại hư cấu, số tiền giữ
   nguyên, tính lũy đẳng, cắt 500 ký tự).
3. **Dịch vụ:** `step_view`/`list_steps`/`run_done_view` + `stream_run` (test unit bằng session giả và hằng số thu nhỏ:
   ping, done sau khi phát hết, `waiting` không đóng, `MAX_STREAM_S`, `Last-Event-ID` lạ, 3 lỗi DB ⇒ `event: error`).
4. **API:** router + quyền xem + bộ đếm chỗ + `TraceStreamResponse`; `/v1/incidents/{id}/run`; gắn vào `main.py`.
5. **Tích hợp:**
   - ASGITransport: `/steps`, luồng của lượt đã `done` (kết thúc tự nhiên), 401/404/429/503, header.
   - Uvicorn thật (`uvicorn.Server` cổng 0, task nền): bước mới, ping, ngắt đột ngột × 50 ⇒ `checkedout()` về mức cũ,
     nối lại không trùng bước, đo SC-001 (n = 30).
6. **Tài liệu và client:** `docs/API.md`, sinh lại client TS + `pnpm --dir apps/web typecheck`, ROADMAP, `evidence.md`.

## 7. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Test với uvicorn thật chập chờn trên CI | Cổng 0, chờ `server.started`, mọi chờ đều có `asyncio.timeout`; ngưỡng SC-001 chỉ khẳng định trên máy dev, CI chỉ kiểm p95 ≤ 1 s |
| Node mới ghi PII vào `output` | Hai lớp che + test "đầu độc" trên mọi khóa cấm |
| Client web không gửi được header bằng `EventSource` | Hợp đồng ghi rõ: dùng `fetch` + `ReadableStream` (027/033); không bao giờ nhận token qua query |
| Lượt kẹt ở `running` vì node ném lỗi (`ainvoke` lỗi ⇒ `_set_status` không chạy; chỉ `recover()` lúc khởi động mới đặt `failed`) | Luồng không có `done`: đóng theo `MAX_STREAM_S`, client nối lại và vẫn thấy `running`. Không sửa runtime ở spec này (ranh giới `agents/**`); ghi vào ROADMAP "Ghi chú" |
| Caddy nén hoặc đệm luồng | Có `X-Accel-Buffering: no` + `Cache-Control: no-cache`; 012 phải đo `: ping` qua Caddy thật (ghi trong evidence) |
