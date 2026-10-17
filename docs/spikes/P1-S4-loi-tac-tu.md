# Spike P1-S4: Lõi tác tử (LangGraph + checkpoint Postgres + bộ hẹn giờ bằng job)

- Thời gian: 14/10/2026 (sớm so với lịch 26/10–04/11) · Nhánh `feat/p1-s4-agent-core` · Quyết định: **ADR-009**
- Ngưỡng theo ROADMAP: đồ thị 2 interrupt + `AsyncPostgresSaver`; chạy tiếp sau `kill -9`; hẹn giờ bằng job; MCP
  `threat`; `agent_steps`; che PII; so Haiku 4.5 với Flash-Lite; **p95 một lượt ≤ 8 s; ghi chi phí**.
- Kết luận ngắn:
  - Phần điều phối **đạt**: đủ 2 interrupt, sống sót qua kill -9, bộ hẹn giờ chạy bằng job, MCP `threat` chạy được, có
    trace, có che PII.
  - **Chưa so được model**: chưa có khóa API (P0-08). Mọi bước LLM đã đo ở chế độ rơi về mẫu.
  - p95 ≤ 8 s: phần điều phối có p50 ≈ 0,13 s, cộng trần LLM 4 s; đuôi p95 trên máy dev bị swap thổi phồng
    ⇒ phải đo lại trên VPS (P1-09).

## 1. Đã dựng

| Thành phần | Tệp | Ghi chú |
|---|---|---|
| Đồ thị sự cố | `backend/src/hoicon/agents/incident_graph.py` | `ingest → fast_alert → risk_scorer ⇄ [ask_elder] → intervention → [await_guardian ⟲ T1/T2] → resolve` |
| Chạy đồ thị | `agents/runtime.py` | `AsyncPostgresSaver` trên pool psycopg, `durability="sync"`. Khóa `pg_advisory_lock` theo thread, có `lock_timeout` 10 s. `resume(expect=…)` bỏ qua giá trị đến muộn. `recover()` chạy tiếp các run dở dang. **Một cửa kiểm dữ liệu**: `start()` tra danh sách đe dọa rồi bỏ `h1` + tên gói khỏi state; `clean_resume()` chỉ giữ khóa hợp lệ, đổi lời kể tự do thành cờ (xem §2b). Tắt cứng LangSmith |
| Cổng LLM | `agents/llm_router.py` | che PII → `<untrusted>` ở lượt user → trần cứng 4 s, không thử lại → output có cấu trúc (`messages.parse`) → chi phí theo bảng giá → trần chi tiêu/ngày → rơi về mẫu |
| Prompt có phiên bản | `agents/prompts/risk_scorer.md`, `intervention.md` | front-matter `version`; `agent_steps.prompt_version` |
| Câu chữ đã duyệt | `agents/texts.py` | 3 câu hỏi E8 (LLM chỉ chọn mã), 4 mẫu tin cho người giám hộ. Mọi tin mở đầu "Đây là trợ lý AI HỏiCon." (luật 6), diễn tập có nhãn ngay sau câu đó (luật 8) |
| Hàng đợi job | `jobs/queue.py`, `jobs/worker.py` | `FOR UPDATE SKIP LOCKED`, khóa chống trùng `idempotency_key`, thử lại giãn cách 2^n giây (tối đa 5 lần). Chỉ worker đang giữ khóa mới được đánh dấu xong |
| Trace | bảng `agent_runs`, `agent_steps` (migration `0002`, kèm `jobs`) | đầu vào đã che PII, độ trễ, token, chi phí, `fallback_used`, mã lỗi |
| Che và giảm PII | `domain/pii.py` | `mask_text` (che mọi dãy ≥ 4 chữ số, kể cả có dấu cách/chấm/gạch/ngoặc xen giữa: số điện thoại, OTP, STK, CCCD, ngày sinh — trừ số tiền có đơn vị; email), `note_flags` (5 cờ từ khóa, có/không dấu), `hmac_h1` (ADR-006) |
| Mức rủi ro | `domain/risk.py` | `raise_only(floor, …)`: không bao giờ dưới `rule_floor` |
| Hợp đồng sự kiện | `domain/events.py` | Pydantic `RiskEvent` khớp `docs/schemas/risk_event.v1.json` (có test enum) |
| MCP `threat` | `mcp_servers/threat.py`, gắn tại `/mcp/threat` **chỉ khi `HOICON_ENV=dev`** | MCP Python SDK 2.3 (`MCPServer`, streamable HTTP, stateless, JSON). Tool `lookup_phone(h1)`. Kiểm Host localhost của SDK chỉ chống DNS rebinding, **không phải xác thực** |
| CLI spike | `agents/spike.py` | `demo`, `bench --n`, `recover`, `crash` (chỉ cho test) |

Thư viện mới (có lý do, CLAUDE.md luật 14): `langgraph` 1.2.15 + `langgraph-checkpoint-postgres` 3.1.3 (stack đã chốt,
ADR-002); `anthropic` 1.13.0 (SDK chính thức, skill `claude-api`); `mcp` 2.3.0 (SDK MCP chính thức, ARCHITECTURE §4).

## 2. Kết quả đo (máy dev Windows, Postgres 17 trong Docker, **chưa có khóa LLM**)

| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| Test backend | **86/86 xanh** (2 lượt liên tiếp): unit (gồm MCP qua HTTP thật), hợp đồng, tích hợp với Postgres | `uv run --directory backend pytest` |
| 2 interrupt + hẹn giờ | `ask_elder` (hẹn giờ 60 s) và `await_guardian` (T1 nhắc 2', T2 chuyển người giám hộ 2 sau 5', T3 dừng chờ 15'); T1/T2 do worker đẩy vào đồ thị; hẹn giờ đến muộn bị bỏ qua (`expect`) | `test_full_incident_flow`, `test_guardian_silence_ends_as_no_response` |
| Chạy tiếp sau **kill -9** | Tiến trình con bị giết (TerminateProcess/SIGKILL) khi đang ở giữa `risk_scorer`. Tiến trình mới `recover()` chạy tiếp từ checkpoint, tới `ask_elder`. `ingest`/`fast_alert` **không chạy lại**; tin `fast_alert` chỉ 1 job | `test_resumes_after_kill_9_without_duplicate_side_effects` (đạt trên Windows) |
| LLM chỉ nâng mức | LLM giả trả `low` cho sự cố mức sàn `high` + số trong danh sách đe dọa ⇒ vẫn `critical` | như trên |
| Không lưu dữ liệu thô | Quét **toàn bộ byte** LangGraph đã ghi cho thread (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`): không có OTP, số điện thoại trong lời kể, `h1` của số gọi đến, tên gói app. LLM nhét số + link vào tóm tắt ⇒ tóm tắt bị thay bằng câu mẫu | `test_full_incident_flow`, `test_pii.py`, `test_runtime_inputs.py`, `test_llm_router.py` |
| Công khai AI | 100% tin tới người giám hộ và câu hỏi E8 mở đầu bằng câu công khai, kể cả khi diễn tập | `test_texts_and_threat.py` + test tích hợp |
| Độ trễ điều phối (n=20, LLM rơi về mẫu) | start→ask_elder p50 **0,125 s**, p95 4,09 s · answer→await_guardian p50 **0,141 s**, p95 4,52 s · decision→done p50 **0,109 s**, p95 2,86 s | `python -m hoicon.agents.spike bench --n 20` |
| Độ trễ trong node | p50 0–30 ms; p95 ≤ 1 s (các node ghi DB) | `agent_steps.latency_ms` |
| Chi phí | 0 USD (chưa gọi LLM thật). Mỗi lượt gọi đều tính chi phí vào `agent_steps.cost_usd` và cộng dồn vào `agent_runs.cost_usd` (có test) | |

**Đọc số độ trễ cho đúng:** lúc đo, máy dev chỉ còn 0,5–0,9 GB RAM trống và Windows đã hết bộ nhớ cam kết (Gradle bị sập
cùng ngày). Đuôi p95 3–4,5 s nằm ngoài node: ghi checkpoint và khóa, khi máy đang swap. Không dùng p95 này để kết
luận. Đo lại trên VPS (P1-09) bằng cùng lệnh `bench`.

**Ngân sách một lượt** = điều phối + một lời gọi LLM (trần cứng 4 s, quá hạn thì dùng mẫu). Mục tiêu p95 ≤ 8 s đạt nếu
p95 điều phối < 4 s; p50 đo được là 0,13 s.

## 2b. Sửa theo review bảo mật (14/10: 0 Critical · 3 High · 3 Medium · 9 Low — đã sửa hết)

| ID | Lỗi | Đã sửa |
|---|---|---|
| H1 | `Command(resume=…)` ghi nguyên giá trị (gồm lời kể thô) vào `checkpoint_writes` TRƯỚC khi node kịp che | `IncidentRuntime.resume` → `clean_resume()`: chỉ giữ `answer/timeout/decision/timer` hợp lệ; lời kể tự do **không bao giờ được lưu**, chỉ còn 5 cờ tất định. Test quét byte của bảng checkpoint |
| H2 | `h1` (dò ngược được ra số điện thoại) và tên gói app nằm trong state/checkpoint, trái ADR-006 | tra `threat` ở `start()`, bỏ `h1` + `package` khỏi state. Test quét byte |
| H3 | Chuỗi chèn lệnh có thể tới tin Zalo (lời kể vào `<context>`, tóm tắt LLM chỉ được che số) | LLM chỉ nhận enum + cờ, không có văn bản tự do; tóm tắt có chữ số/link/tên miền/@/tên kênh chat ⇒ dùng câu mẫu; `<`/`>` trong dữ liệu bị đổi để không đóng/mở thẻ được |
| M1 | `mask_text` lọt `OTP123456`, `(090) 000-0001`, OTP đọc rời từng số, ngày sinh… | che mọi dãy ≥ 4 chữ số có dấu phân cách xen giữa (trừ số tiền có đơn vị); 19 ca thử |
| M2 | Lời kể (tên thật, địa điểm không che được) gửi ra nước ngoài khi chưa có đồng ý `llm_processing` | không gửi lời kể cho LLM (chỉ cờ) |
| M3 | Kiểm Host localhost bị hiểu nhầm là xác thực | MCP chỉ gắn ở dev; ghi rõ trong ADR-009/README |
| L1–L9 | router chỉ bắt vài lớp lỗi; ngân sách đọc-rồi-ghi; LLM làm nhẹ lời khuyên ở mức rất cao; tin thiếu cờ `is_drill/is_demo`; hủy hẹn giờ quá sớm có thể kẹt sự cố sau kill -9; LangSmith; hạn lưu checkpoint; cách xưng hô có thể là họ tên; chờ khóa vô hạn | bắt mọi `Exception`; giữ chỗ ngân sách trước khi gọi; mức critical luôn "gọi ngay và giữ máy"; payload có `is_drill/is_demo`; giữ hẹn giờ (đến muộn thì `expect` bỏ qua); tắt cứng LangSmith; thêm hạn lưu vào DATA-MODEL §6; kiểm cách xưng hô ≤ 20 ký tự, không chữ số, LLM chỉ thấy `{alias}`; `lock_timeout` 10 s |

## 3. So sánh model (chưa chạy — chờ khóa API, P0-08)

| Model | Giá (USD/1M token vào/ra) | Ghi chú |
|---|---|---|
| Claude Haiku 4.5 (`claude-haiku-4-5`) | 1,00 / 5,00 | model nêu trong ROADMAP; không có `effort` |
| **Claude Haiku 5.5** (`claude-haiku-5-5`) | **0,10 / 0,50** (prompt ≤ 100K) | Haiku thế hệ hiện tại. Router tắt thinking và đặt `effort: low` cho bước phân loại. **Mặc định tạm thời** |
| Gemini Flash-Lite | — | chưa viết provider (chưa có khóa, chưa thử được) |

Ước tính chi phí một sự cố, **chưa đo**: 3 lời gọi (`risk_scorer` ×2 + `intervention`), mỗi lời gọi ~1,2K token vào và
~150 token ra ⇒ Haiku 4.5 ≈ 0,006 USD, Haiku 5.5 ≈ 0,0006 USD.

Cách chạy khi có khóa (công cụ đã sẵn từ spec 003; JSON theo `docs/schemas/bench_report.v1.json`, có `llm_mode` để không
nhầm số điều phối với số của model):

```
uv run --directory backend python -m hoicon.agents.spike bench --n 20 --model claude-haiku-4-5 --json haiku-4-5.json
uv run --directory backend python -m hoicon.agents.spike bench --n 20 --model claude-haiku-5-5 --json haiku-5-5.json
```

So sánh độ trễ, chi phí, tỷ lệ rơi về mẫu, và đầu ra trên bộ eval smoke. Bộ eval chưa có (P1-07 kịch bản, P2-15
`hoicon-eval`) ⇒ chất lượng so sánh trên các kịch bản P1-07 khi có.

## 4. Rủi ro và việc còn lại

| Việc | Khi nào |
|---|---|
| Khóa API ⇒ đo độ trễ và chi phí thật của Haiku 4.5 / 5.5; quyết định model; provider Gemini nếu còn cần | ngay khi P0-08 xong |
| Đo lại p95 trên VPS | P1-09 |
| `IncidentService.transition` + bảng `incidents`; nối đồ thị vào `POST /v1/events` (khởi động runtime + worker trong lifespan) | P2-03 |
| Gửi tin thật qua Zalo, có bộ kiểm hạn mức `messages_out` (handler `notify_guardian` hiện chỉ ghi log) | P1-S3 / P2-07 |
| ✅ (spec 003, 15/10) `threat_indicators` chỉ HMAC + lệnh nạp; token + giới hạn tần suất cho `/mcp/threat` (đã đóng lỗ hổng dò danh sách bằng cách thử hết số). **Còn:** nguồn danh sách thật + quy trình gắn cờ (P3); mở `/mcp/threat` ra Internet khi spec 012 chốt Caddy | P3 · 012 |
| Lưu `phone_hmac` của số gọi đến (cần pepper) cùng sự cố cho bước xác minh | P2-03 |
| Nhận dạng tên riêng (NER) + đồng ý `llm_processing` trước khi cân nhắc gửi lời kể (đã che) cho LLM | sau P1-06 |
| `run-eval smoke` cho prompt (chưa có bộ eval) | P2-15 |
| ✅ (spec 003) Trần chi tiêu/ngày đọc `SUM(agent_steps.cost_usd)` (giờ Việt Nam) + giữ chỗ trong tiến trình. **Còn:** chi phí lời gọi quá hạn mà vẫn bị tính tiền không vào `agent_steps` (sai số ≤ một lời gọi) | P2-04 |
| Job hạn lưu: `agent_steps` 30 ngày (DATA-MODEL §6); checkpoint LangGraph theo hạn của sự cố | P2-20 |
