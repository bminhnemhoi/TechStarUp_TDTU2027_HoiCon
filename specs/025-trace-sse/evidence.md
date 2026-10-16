# Bằng chứng nghiệm thu Spec 025: Luồng SSE truy vết tác tử

- **Trạng thái**: code, test và tài liệu xong (T001–T014). Review độc lập: xem mục "Review độc lập". CI trên PR **chưa chạy** (chưa commit/push).
- **Môi trường đo**: máy dev Linux CachyOS, Postgres dev (Docker, cổng 15432), uvicorn thật chạy ở `127.0.0.1` cổng ngẫu nhiên, ngày 16/10/2026.
- **Nguồn số**: chỉ máy dev, localhost. Chưa có Caddy/VPS (thuộc 012), nên mọi số "qua reverse proxy" là **CHƯA ĐO**.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 độ trễ bước → client | p95 ≤ 500 ms, n ≥ 30 | `test_trace_sse_live.py -s` (uvicorn thật, localhost, `POLL_S = 0,3 s`; 30 bước rải pha so với nhịp thăm dò; đo từ lúc commit xong tới lúc nhận đủ khung `event: step`) | 5 lần chạy: p50 = 179–224 ms, p95 = 301–303 ms, max ≤ 304 ms (lần cuối, sau các sửa review: p50 224 · p95 301) | ĐẠT trên máy dev (CI chỉ khẳng định p95 ≤ 1 s) |
| SC-002 che PII | 0 SĐT thô · 0 hex ≥ 32 · 0 khóa cấm · không có `input_redacted` | `test_api_runs.py::test_poisoned_steps_leak_nothing_on_either_endpoint` (4 bước "đầu độc": SĐT hư cấu thô, hex 64, khóa `h1`/`phone`/`note`/`text`, token 43 ký tự, `input_redacted` có SĐT) trên CẢ `/steps` và SSE + `test_redact_json.py` (19 ca) | 0 / 0 / 0 / không có; số tiền `20.000.000 đồng` giữ nguyên | ĐẠT |
| SC-003 `: ping` mỗi 15 s | có ping sau `PING_S` im lặng; đi qua Caddy | `test_trace_stream.py` (đồng hồ thu nhỏ) + `test_trace_sse_live.py::test_ping_is_sent_when_nothing_happens` (`PING_S = 0,4 s` trên uvicorn thật: ping đến sau 0,35–1,5 s, rồi đều đặn) | Đạt với `PING_S` thu nhỏ; giá trị thật 15 s chưa chờ trong test | ĐẠT (đơn vị + localhost) · qua Caddy **CHƯA ĐO** (012) |
| SC-004 lịch sử `/steps` | khớp DB theo `(at, id)`, giống payload SSE; 401/404 | `test_api_runs.py` (khớp DB; 5 bước cùng `at` trả đủ theo thứ tự `id`; SSE giống hệt `/steps`; 401 thiếu/sai token và token qua query; 404 nhà khác / lượt `eval-…` / lượt trỏ tới sự cố không tồn tại / id lạ, cùng một câu trả lời) | Đạt | ĐẠT |
| SC-005 `event: done` | đúng 1 lần, sau bước cuối, số đếm/chi phí khớp DB; `waiting` không đóng | `test_trace_stream.py` (done sau bước cuối kể cả khi lượt kết thúc NGAY SAU câu đọc trạng thái; `waiting` không đóng; `failed` cũng `done`) + `test_api_runs.py` (`total_steps = 4`, `cost_usd = 0.002450` khớp DB) + `test_trace_sse_live.py` (bước chèn trong lúc stream, rồi `done` với `total_steps = 30`; nối lại bằng `Last-Event-ID` không nhận trùng) | Đạt | ĐẠT |
| SC-006 không rò tài nguyên | `checkedout()` + bộ đếm về mức cũ sau 50 lần ngắt; 503 khi vượt trần | `test_trace_sse_live.py::test_fifty_abrupt_disconnects…` (50 kết nối thô, ngắt bằng RST sau khi luồng đã bắt đầu; trần nới để 50 luồng sống cùng lúc) + `test_api_runs.py` (429 ở luồng thứ 4 của cùng một người, 503 + `Retry-After: 5` khi đủ `MAX_STREAMS`, 404 trả trước khi giữ chỗ) | Sau 50 lần ngắt: bộ đếm chỗ về 0, `pool.checkedout()` bằng mức ban đầu; API vẫn phục vụ | ĐẠT |

## Lệnh đã chạy (T013)

| Lệnh | Kết quả |
|---|---|
| `uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache` | **1180 passed** (155 test mới: gồm `redact_json`, stream/chỗ/response, hợp đồng, API, live và các ca `mask_text` thêm vào `test_pii.py`; bộ cũ không hỏng test nào) |
| `ruff check` / `ruff format --check` (`--cache-dir /tmp/ruff_cache src/ tests/`) | sạch / 145 file đã đúng định dạng |
| gitleaks từng thư mục: `backend/src`, `backend/tests`, `docs/schemas`, `specs/025-trace-sse` | không phát hiện gì |
| `hoicon-eval --suite smoke --compare baseline` (chạy làm hồi quy; không đổi đồ thị/prompt) | ĐẠT: 20 ca · recall 100% · báo nhầm 0% · vi phạm 0 · công khai AI 100% · so baseline +0,0 / +0,0 điểm % |
| `python3 scripts/check-spec-trace.py` | 12 spec, 0 lỗi |
| `bash scripts/gen-api-client.sh && pnpm --dir apps/web typecheck` | sinh lại `openapi.json` + `schema.d.ts` (có `/v1/runs/{run_id}/stream` với `text/event-stream`); typecheck xanh. Diff lớn vì client chưa được sinh lại từ spec 020 (FR-008 yêu cầu gom) |
| `git diff --stat -- backend/src/hoicon/agents backend/src/hoicon/prompts backend/src/hoicon/jobs` | rỗng (không đụng hành vi tác tử) |

## Độ nhạy của test (đột biến, hoàn nguyên sau mỗi lần)

30/30 đột biến áp được đều làm test đỏ (10 lần đầu + 7 sau review lượt 1 + 8 sau review lượt 2 + 5 sau review lượt 3; một đột biến sống sót lúc đầu vì assertion `\d{4}` không thấy số điện thoại viết có dấu chấm — đã siết thành đếm chữ số còn lại ≤ 3): bỏ `aclose()` trong `TraceStreamResponse`; không nhả chỗ; con trỏ chỉ theo `at` (bỏ `id`); `step_view` bỏ `redact_json`; `step_view` thêm `input_redacted`; `redact_json` không bỏ khóa cấm; không kiểm gia đình; bỏ `DB_FAIL_LIMIT`; coi `waiting` là kết thúc; bỏ trần mỗi người; khóa cấm chỉ so khớp tên chính xác; miễn che mọi số có đơn vị tiền; bỏ trần theo gia đình; không escape U+2028; không bắt lỗi dựng bước; hex ngắt dấu cách không che; số nguyên cực lớn không bị chặn; số tiền: bỏ kiểm mở đầu 0/+, bỏ kiểm tròn triệu; khóa: bỏ hậu tố an toàn; token: bỏ ngưỡng tỉ lệ dấu gạch; bỏ giữ UUID/mốc giờ; bước hỏng `retryable:true`; `ValueError` không tính lỗi DB; thông báo giới hạn không phân biệt.

## Review độc lập

`security-privacy-reviewer` (dựng Postgres tạm cổng 25432, không đụng DB dev; chạy 552 test unit/contract/integration xanh, thăm dò thêm bằng script riêng): **0 Critical · 0 High · 4 Medium · 6 Low**. Phân quyền (run → `thread_id` → `Incident.family_id`, lượt `eval-…`, token qua query, JWT thiết bị), bộ đếm chỗ (không đua, không rò chỗ/kết nối sau 50 lần ngắt), không giữ session qua `yield`, thứ tự `done`, khung SSE không vỡ bởi `\r\n`, fuzz 20.000 số điện thoại chia nhỏ và tính lũy đẳng đều **ổn**.

| # | Mức | Phát hiện | Xử lý |
|---|---|---|---|
| 1 | Medium | Khóa cấm chỉ khớp tên chính xác: `"H1 "`, `"ｈ1"`, `package_name`, `note_text`, `caller_phone`, `zalo_id` lọt | **Đã sửa**: chuẩn hóa NFKC, tách từ (kể cả camelCase), bỏ khóa nếu có từ cấm hoặc ghép lại trùng khóa cấm; test cho 10 biến thể + khóa vô hại (`context`, `tokens_in`) vẫn giữ |
| 2 | Medium | `mask_text` miễn che mọi số có đơn vị tiền: `0900000123 tr/k/đ` ra nguyên văn (cũng ảnh hưởng `llm_router`/`incident_graph`) | **Đã sửa**: chỉ miễn khi đúng dạng tiền (nhóm nghìn chuẩn, hoặc ≤ 9 chữ số không mở đầu bằng 0/+); test số tiền thật vẫn giữ |
| 3 | Medium | Hex ngắt bằng dấu cách/`:`/`-`, token 32–39 ký tự, base64 chuẩn có `=`/`+` lọt | **Đã sửa một phần**: hex ngắt ⇒ `[HASH]`; đoạn ≥ 32 ký tự có cả chữ lẫn số hoặc ≥ 40 ký tự (nay gồm `+`, `=`) ⇒ `[TOKEN]`. Còn lại: base64 chuẩn có `/` bị tách thành đoạn ngắn |
| 4 | Medium (nghi vấn) | Không có trần theo gia đình: 4 gia đình × 2 người giám hộ × 3 luồng có thể chiếm hết 20 chỗ | **Đã sửa**: `MAX_STREAMS_PER_FAMILY = 4` (429). Nhiều gia đình hợp tác vẫn có thể chiếm 20 chỗ (cần giới hạn tần suất mở luồng/đăng ký gia đình, chưa có) |
| 5 | Low | U+2028/2029/0085 không bị escape trong `data:` | **Đã sửa** (+ `allow_nan=False`) |
| 6 | Low | Bước không dựng được (số nguyên 5000 chữ số ghi thẳng vào JSONB) làm `/steps` 500, SSE chết im | **Đã sửa**: `redact_json` chặn số lớn/NaN; SSE gửi `event: error` rồi đóng. `/steps` vẫn 500 nếu dữ liệu hỏng kiểu khác (cần ghi thẳng DB) |
| 7 | Low | `Last-Event-ID` mất `max_length` nhưng client/`openapi.json` ghi 64 | **Đã sửa**: chọn "header rác ⇒ phát lại từ đầu" (đúng spec), client sinh lại, có test với `x*500`, rác, `0` |
| 8 | Low | Luồng đang mở làm treo tắt máy tới 600 s | **Ghi nhận**: cần `--timeout-graceful-shutdown` khi chạy (đã ghi vào `docs/API.md`); chưa đo |
| 9 | Low | Thiếu `no-transform`; `/steps` thiếu `Cache-Control` | **Đã sửa**: `no-cache, no-transform` (stream), `no-store` (`/steps`) |
| 10 | Low | 404 nhà khác tốn 2 truy vấn, id lạ 1 | **Chấp nhận**: UUIDv7 khó đoán, chênh mili-giây khó khai thác |

Ghi chú nhỏ của reviewer: quyền xem chỉ kiểm lúc kết nối (người giám hộ bị xóa thì luồng đang mở sống tối đa 600 s).

### Lượt 2 (đọc lại các sửa): 0 Critical · **1 High** · 3 Medium · 4 Low

Lượt 1 đã khắc phục đúng phần lớn nhưng chính các sửa sinh lỗi mới; bộ test cũ vẫn xanh vì chưa có ca cho chúng.

| # | Mức | Phát hiện | Xử lý |
|---|---|---|---|
| 1 | **High** | Số điện thoại đội lốt số tiền vẫn lọt (fuzz 40.000 số): `900000123 k`, `0.900.000.123 đ`, `090.000.123 đ`, `0,900,000,123 k`, `1.234.567.890.123 k` | **Đã sửa**: miễn che chỉ khi không mở đầu 0/+, ≤ 12 chữ số, và từ 10 chữ số (hoặc 9 chữ số mở đầu 3/5/7/8/9) phải tròn triệu; `mask_text` nay nối cả dấu phẩy dính liền giữa các chữ số. Test fuzz 3.000 số (tự viết lúc đầu cũng sót phần này vì dùng regex `\d{4}`; đã siết) |
| 2 | Medium | Khóa vô hại bị bỏ nhầm: `note_flags` (output thật của `ask_elder`), `text_len`, `token_count`, `caller_flagged`, `zalo_sent` | **Đã sửa**: từ cuối của khóa là `flags/flag/flagged/len/length/count/sent/kind/type` ⇒ giữ; thêm test trên đúng output của `ask_elder` |
| 3 | Medium | UUID và định danh dài (`intervention_guardian_brief_prompt_v2_final`) bị che thành `[TOKEN]` | **Đã sửa**: token cần ít dấu `_`/`-` (< 10%) và có độ ngẫu nhiên (≥ 40 ký tự có số/HOA, hoặc 32–39 ký tự đủ HOA + thường + số); UUID chuẩn và mốc giờ ISO có `T` được giữ nguyên. Còn lại: token có ≥ 10% dấu `_`/`-` (xác suất thấp với token urlsafe) không bị che bởi lớp này |
| 4 | Medium | Số tiền thật lớn (`1500000000 đ`) bị che nhầm | **Đã sửa** cùng #1 (giữ khi tròn triệu); số tiền lớn không tròn triệu và không có dấu nhóm vẫn bị che (chấp nhận, thiên về an toàn) |
| 5 | Low | `ValueError` khi nạp hàng (số 5000 chữ số) vẫn làm SSE nổ; `retryable:true` làm client lặp mãi trên bước hỏng | **Đã sửa**: `ValueError` tính là lỗi DB; bước không dựng được ⇒ `{"retryable":false}` |
| 6 | Low | Trần theo gia đình dùng chung thông báo "Bạn đang mở quá nhiều…" | **Đã sửa**: phân biệt `member`/`family`/`global` (có test) |
| 7 | Low | Chuỗi chỉ toàn chữ số tách cặp bị `[HASH]` | **Đã sửa**: chỉ `[HASH]` khi có ký tự a–f |
| 8 | Low | Mốc giờ ISO bị `mask_text` phá | **Đã sửa** trong `redact_json` (ngày sinh trần vẫn bị che) |

Phát hiện này gợi ý một bài học đã ghi lại: **một assertion `\d{4}` bỏ sót số có dấu chấm** — mọi test PII mới nên đếm chữ số còn lại.

### Lượt 3 (đọc lại các sửa lượt 2): 0 Critical · 0 High · 3 Medium · 4 Low

Fuzz 17 dạng số điện thoại đi kèm đơn vị tiền × 40.000 mẫu: **0 lọt**. Các sửa lượt 2 đóng đúng lỗ hổng chính; ba chỗ hở mới do chính chúng:

| # | Mức | Phát hiện | Xử lý |
|---|---|---|---|
| 1 | Medium | UUID/mốc giờ được giữ nguyên nên giấu được số điện thoại (`00000000-0000-1000-8000-090000012345`, phân số giây dài `…00.0900000123`) | **Đã sửa**: phân số giây `\d{1,6}` và phải đứng cuối; UUID chứa dãy ≥ 10 chữ số liền nhau không được miễn che; test cho cả ba dạng |
| 2 | Medium | Token urlsafe thật lọt ~1% (tỉ lệ `_-` ≥ 10%) | **Đã sửa**: ≥ 32 ký tự có CẢ chữ HOA lẫn thường ⇒ `[TOKEN]` bất kể tỉ lệ dấu; test 8.000 token `secrets.token_urlsafe` (24/28/32/40 byte) đều bị che. Còn lại: base64 chuẩn có `/` bị tách đoạn; token < 32 ký tự |
| 3 | Medium | Khóa hậu tố an toàn (`phone_type`, `token_kind`, `note_count`…) giữ nguyên giá trị tự do | **Đã sửa**: khóa loại này chỉ giữ giá trị là cờ/số/None, chuỗi giống enum (`[a-z_]{1,32}`) hoặc dict/list chỉ gồm chúng. Còn lại: khóa viết liền (`phonenumber`) không bị bỏ vì không tách được từ (đánh đổi để không bỏ nhầm `phoneme`) |
| 4 | Low | `ValueError` im lặng, rồi `retryable:true` làm client nối lại mãi | **Đã sửa**: `ValueError` ⇒ `event: error {"retryable":false}` ngay, log mức warning (chỉ tên lớp lỗi) |
| 5 | Low | Nối dấu phẩy làm `1,2,3,4` ⇒ `[MÃ]` | **Đã sửa**: chỉ nối dấu phẩy khi đứng trước đúng 3 chữ số (dấu nhóm nghìn) |
| 6 | Low | Dấu ngăn cách lạ vẫn lộ 6 số cuối (`0900, 000, 123`, `0900:000:123`, `0900*000*123`) | **Ghi nhận** (hành vi có từ trước của `mask_text`; đã ghi ROADMAP) |
| 7 | Low | Số điện thoại "tròn triệu" (`912000000 k`, `84912000000 tr`) vẫn được miễn che; tiền hợp lệ không tròn ≥ 10 chữ số bị che | **Chấp nhận** (đánh đổi đã nêu, ~1/10⁶) |

**Các sửa lượt 3 chưa có reviewer đọc lại.** Sau ba lượt không còn Critical/High; mỗi lượt tìm ra lỗi mới nhỏ hơn ở chính các sửa của lượt trước, nên tôi dừng vòng review ở đây và để Tiến/Minh đọc PR.

## Điều cần biết / chưa làm

- **Chưa đo qua Caddy/VPS**: `: ping` qua proxy thật, đệm/nén, hạn chờ đọc — để 012.
- **Hạn mức luồng đếm trong bộ nhớ**: đúng với một tiến trình (ADR-002); nhiều worker nhân hạn mức lên.
- **Lượt kẹt `running`** (node ném lỗi nên `_set_status` không chạy; chỉ `recover()` lúc khởi động mới đặt `failed`): luồng không có `done`, đóng theo `MAX_STREAM_S = 600 s`, client nối lại vẫn thấy `running`. Không sửa runtime ở spec này (ranh giới `agents/**`) — đã ghi vào ROADMAP.
- **`agent_runs.incident_id` chưa được ghi** khi tạo lượt; liên kết sự cố ↔ lượt dựa vào `thread_id = str(incident.id)`. Đã ghi vào ROADMAP "Ghi chú".
- **Giao diện** (027/033) chưa có; client web phải dùng `fetch` + `ReadableStream` (không dùng `EventSource`), tự nối lại theo `retry` và gửi `Last-Event-ID`.
- **Chưa chạy trên Windows**; **CI trên PR**: chưa commit/push.
