# Spec 025: Luồng SSE truy vết tác tử (Agent Steps SSE Trace Stream)

**Mã ROADMAP**: `P2-10` · **Làn**: B (server) · **Phụ thuộc**: `021-events-incident-service`, `024-risk-and-intervention`
· **Người dùng sau**: `027-guardian-web` (người giám hộ), `033-web-sim-eval` (`/trace`) · **Cột mốc**: Gate M2
· **Nhánh**: `feat/025-trace-sse` · **ADR**: ADR-002 (một tiến trình), ADR-006 (không PII thô), ADR-009 (llm_router, LLM chỉ nâng)

---

## 1. Bối cảnh & mục tiêu

Đồ thị sự cố (`IncidentRuntime`, spec 021/024) đã ghi mỗi node thành một dòng `agent_steps`
(`backend/src/hoicon/agents/incident_graph.py`, hàm `step()`): `ingest`, `fast_alert`, `risk_scorer`, `ask_elder`,
`intervention`, `await_guardian`, `resolve`. Trạng thái lượt chạy nằm ở `agent_runs.status`
(`running` · `waiting` · `done` · `failed`, do `IncidentRuntime._set_status` ghi). Hiện chưa có đường nào để đọc
dữ liệu này từ bên ngoài.

**User story.** Là người giám hộ, khi bố mẹ có sự cố, tôi muốn xem trợ lý AI đang làm gì (đã chấm mức nào, đã hỏi bố mẹ
chưa, đang chờ tôi quyết hay đã đóng), cập nhật ngay khi có bước mới, để tin vào cảnh báo và biết khi nào cần gọi. Trang
web của người giám hộ (027) và trang `/trace` (033) dùng chung luồng dữ liệu của spec này.

**Phạm vi:** chỉ máy chủ. Gồm hợp đồng, bộ che dữ liệu, dịch vụ đọc bước, SSE, các route, test và client TS sinh lại.
Phần giao diện web nằm ở 027 và 033.

### Hiện trạng code cần biết (đã đọc 16/10/2026)

- `agent_steps` có chỉ mục `ix_agent_steps_run_at (run_id, at)`; `id` là UUIDv7 (`db/ids.py`) ⇒ không cần migration.
- `agent_runs.incident_id` **không được ghi** khi tạo lượt; liên kết sự cố ↔ lượt là `agent_runs.thread_id = str(incidents.id)`.
  Lượt eval có `thread_id = "eval-…"` (không có sự cố) ⇒ không ai ngoài ops xem được.
- `mask_text` (`domain/pii.py`) che email + dãy ≥ 4 chữ số, **không** che chuỗi hex 64 ký tự (`h1`/HMAC) một cách tin cậy
  (chỉ thay các cụm số bên trong, để lại các chữ a–f) ⇒ cần bộ che riêng cho JSON (FR-002).
- `input_redacted` của bước LLM là `{"context": <ngữ cảnh gửi LLM đã che>, "untrusted": bool}`. Đó là dữ liệu đầu vào mô
  hình, người giám hộ không cần ⇒ **không xuất** (tối thiểu hóa dữ liệu). `/trace` của ops nếu cần sẽ thêm ở 033.
- Xác thực người giám hộ: `get_current_guardian` (`api/auth.py`, JWT `aud=hoicon-guardian`). Pool DB: `pool_size=5` + tràn
  mặc định 10 (`db/session.py`), dùng chung với worker trong tiến trình API (spec 024).

## 2. Tiêu chí thành công

- **(SC-001)** Độ trễ: từ lúc dòng `agent_steps` được commit tới lúc client nhận đủ khung `event: step`, **p95 ≤ 500 ms**,
  n ≥ 30 bước, đo qua uvicorn thật trên localhost (máy dev; số qua Caddy/VPS đo ở 012, ghi rõ nguồn).
- **(SC-002)** Che PII 100%: trên luồng SSE và `/steps` của một lượt có bước bị "đầu độc" (số điện thoại hư cấu thô, chuỗi
  hex 64 ký tự, khóa `h1`/`package`/`token`/`note`, token 43 ký tự), kết quả có **0** số điện thoại thô, **0** chuỗi hex
  ≥ 32 ký tự, **0** khóa bị cấm ở mọi độ sâu, và không có trường `input_redacted`.
- **(SC-003)** Giữ kết nối: khi không có bước mới, server gửi dòng chú thích `: ping` sau mỗi `PING_S = 15 s` kể từ lần
  ghi cuối (test chạy với `PING_S` thu nhỏ). Chưa kiểm được qua Caddy vì chưa có hạ tầng 012; evidence ghi CHƯA ĐO cho
  phần này.
- **(SC-004)** Lịch sử: `GET /v1/runs/{id}/steps` trả đúng mọi dòng của lượt, theo thứ tự `(at, id)`, và mỗi bước giống
  hệt bản phát qua SSE (cùng một hàm dựng). Thiếu hoặc sai token ⇒ 401. Lượt của gia đình khác, lượt eval hoặc lượt không
  tồn tại ⇒ 404 (không lộ lượt có tồn tại hay không).
- **(SC-005)** Kết thúc tất định: lượt ở `done`/`failed` ⇒ server phát hết các bước còn lại, rồi phát **đúng một**
  `event: done` với `run_id, status, total_steps, cost_usd, is_drill, is_demo` khớp DB, rồi đóng kết nối trong ≤ 1 nhịp
  thăm dò. Lượt `waiting` (đang chờ người giám hộ) **không** đóng luồng. Kết nối lại với `Last-Event-ID` không nhận lại bước đã có.
- **(SC-006)** Không rò tài nguyên: sau 50 lần mở rồi ngắt đột ngột, số kết nối pool đang mượn (`pool.checkedout()`) và bộ
  đếm luồng đang mở trở về mức ban đầu. Không lượt thăm dò nào giữ giao dịch hay kết nối qua một lần `yield`. Mở luồng
  thứ `MAX_STREAMS + 1` ⇒ 503 có `Retry-After`.

## 3. Yêu cầu chức năng

- **(FR-001)** Hợp đồng trước: `docs/schemas/agent_step.v1.json` (một bước đã che, `additionalProperties: false`),
  `docs/schemas/run_steps.v1.json` (phản hồi lịch sử) và `docs/schemas/run_done.v1.json` (payload `event: done`). Mỗi
  schema có fixture `valid`/`invalid` trong `docs/schemas/fixtures/` và test hợp đồng.
- **(FR-002)** Thêm bộ che JSON `redact_json(value)` vào `hoicon.domain.pii`, chạy đệ quy:
  - bỏ khóa trong `TRACE_DENY_KEYS` ở mọi độ sâu;
  - với mỗi chuỗi: thay hex ≥ 32 ký tự bằng `[HASH]`, chuỗi base64url ≥ 40 ký tự bằng `[TOKEN]`, rồi áp `mask_text`, rồi
    cắt ở 500 ký tự;
  - list và dict đi đệ quy, số/bool/None giữ nguyên;
  - tính lũy đẳng: `redact_json(redact_json(x)) == redact_json(x)`.
- **(FR-003)** Thêm dịch vụ `hoicon.services.trace_service`:
  - `step_view(step)` dựng bản xuất theo danh sách trắng cột, `output` đi qua `redact_json`, bỏ `input_redacted`;
  - `list_steps(session, run_id, after=None, limit=500)` đọc theo khóa `(at, id)`;
  - `run_done_view(run, total_steps)`.

  Cả `/steps` và SSE dùng chung các hàm này.
- **(FR-004)** Generator SSE `stream_run(sessions, run_id, last_event_id, is_disconnected)`:
  - khung đầu là `retry: 3000`;
  - `event: step` có `id: <step_id>`, `data` là JSON một dòng;
  - gửi `: ping` khi đã `PING_S` giây không ghi gì;
  - gửi `event: done` khi lượt kết thúc và đã phát hết bước;
  - quá `MAX_STREAM_S = 600 s` mà lượt chưa xong ⇒ đóng luồng, client tự nối lại bằng `Last-Event-ID`;
  - `Last-Event-ID` không thuộc lượt ⇒ phát lại từ đầu.
- **(FR-005)** Quản lý kết nối:
  - **Thăm dò:** mỗi nhịp `POLL_S = 0,3 s` mượn một session ngắn (`async with sessions()`), đọc trạng thái lượt TRƯỚC rồi
    mới đọc bước mới, đóng session TRƯỚC khi `yield`.
  - **Ngắt kết nối:** kiểm `request.is_disconnected()` mỗi nhịp. `CancelledError` và `GeneratorExit` không bao giờ bị nuốt:
    chỉ dọn trong `finally` rồi ném lại.
  - **Giải phóng chắc chắn:** dùng `TraceStreamResponse` (lớp con `StreamingResponse`), có `finally` gọi
    `body_iterator.aclose()` và nhả chỗ trong bộ đếm. Lý do: Starlette 1.7 với ASGI ≥ 2.4 báo ngắt bằng `ClientDisconnect`
    khi ghi và không tự đóng generator.
  - **Giới hạn số luồng:** trần `MAX_STREAMS = 20` cho cả tiến trình (ADR-002) ⇒ 503 + `Retry-After: 5`; trần
    `MAX_STREAMS_PER_MEMBER = 3` ⇒ 429.
  - **Lỗi DB:** lỗi DB 3 nhịp liên tiếp ⇒ gửi `event: error` `{"retryable": true}` rồi đóng luồng; không log nội dung bước.
- **(FR-006)** Router `hoicon.api.routers.runs` (JWT người giám hộ):
  - `GET /v1/runs/{run_id}/steps` (JSON theo `run_steps.v1`);
  - `GET /v1/runs/{run_id}/stream` (`text/event-stream; charset=utf-8`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`).
    Không đặt `Connection: keep-alive`: đây là header hop-by-hop, HTTP/2 cấm.

  Quyền xem: `agent_runs.thread_id` phải parse được thành UUID của sự cố thuộc `claims.family_id`; nếu không ⇒ 404. Mọi mã
  401/404/429/503 trả trước khi luồng bắt đầu. **Cấm** nhận token qua query string (Caddy ghi log URL); client web dùng
  `fetch` có header `Authorization` và đọc luồng.
- **(FR-007)** `GET /v1/incidents/{incident_id}/run` (JWT người giám hộ, cùng gia đình) ⇒ `{"run_id", "status"}`; chưa có
  lượt ⇒ 404. Đây là cách client tìm `run_id` từ sự cố, không phải đổi `IncidentDetail` của thiết bị.
- **(FR-008)** Gắn router vào `api/main.py`; khai báo `responses={200: {"content": {"text/event-stream": {}}}}` cho OpenAPI;
  sinh lại client TS (`scripts/gen-api-client.sh`, cũng gom phần lệch từ spec 020); cập nhật mục "Luồng SSE" trong
  `docs/API.md`.
- **(FR-009)** Test:
  - unit cho `redact_json` và generator (session giả, đồng hồ thu nhỏ);
  - tích hợp qua `ASGITransport` **chỉ cho lượt đã kết thúc** (transport gom hết thân phản hồi nên luồng vô hạn sẽ treo test);
  - tích hợp qua **uvicorn thật** (cổng ngẫu nhiên) cho bước mới, ping, ngắt đột ngột, nối lại và đo độ trễ SC-001.
- **(FR-010)** Nghiệm thu: chạy đủ lệnh kiểm, điền `evidence.md` bằng số đo thật có nguồn, giữ ROADMAP `P2-10` ở ◐ tới khi
  027/033 tiêu thụ được luồng.

## 4. Bất biến & ranh giới

- **ADR-006:** không xuất `h1`, HMAC, tên gói, số điện thoại thô, token hay lời kể tự do. Danh sách trắng cột + `redact_json`
  là hai lớp độc lập. Một lớp sót thì lớp kia vẫn chặn.
- **Không đụng hành vi tác tử:** không sửa `agents/**`, `prompts/**`, `jobs/**`. Spec này chỉ đọc `agent_steps`/`agent_runs`.
  Vì không đổi đồ thị hay prompt, eval smoke không bắt buộc (vẫn được chạy làm hồi quy).
- **Không thêm migration** (chỉ mục đã đủ) và **không thêm thư viện**: SSE tự dựng khung, không dùng `sse-starlette`.
- **Diễn tập/demo:** `run_steps` và `run_done` mang `is_drill`, `is_demo` để giao diện gắn nhãn `[DIỄN TẬP]` (luật 8).
- **Công khai AI:** luồng là dữ liệu máy cho người giám hộ, không phải tin gửi người cao tuổi, nên luật 6 không áp dụng.
  Nếu sau này đưa câu chữ LLM ra luồng thì phải xét lại.

## 5. Ngoài phạm vi

Giao diện web (027, 033) · `/v1/families/{id}/stream`, `/v1/demo/stream` (033/050) · quyền xem của ops và ban giám khảo
(033) · LISTEN/NOTIFY (thăm dò đủ với ≤ 20 luồng) · ghi `agent_runs.incident_id` (ghi vào ROADMAP "Ghi chú") · cấu hình
Caddy (012).
