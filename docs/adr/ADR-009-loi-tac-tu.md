# ADR-009: Lõi tác tử — LangGraph + checkpoint Postgres đồng bộ, hẹn giờ bằng job, cổng LLM duy nhất

- Trạng thái: **Chấp nhận** (cơ chế) · 14/10/2026 · **model chờ đo** (khóa API, P0-08)
- Bằng chứng: spike P1-S4 `docs/spikes/P1-S4-loi-tac-tu.md`
- Liên quan: ADR-002 (một tiến trình FastAPI + LangGraph), ADR-004 (Postgres làm hàng đợi), ADR-006 (băm số), CLAUDE.md luật 5–6

## Bối cảnh
Sau khi máy đã cho người cao tuổi dừng an toàn, máy chủ phải: báo con cháu ngay, hỏi thêm người cao tuổi, chờ người giám
hộ phản hồi (có thể vài phút), nhắc lại và chuyển người thứ hai nếu im lặng. Tất cả phải sống sót khi tiến trình khởi
động lại. LLM chỉ được nâng rủi ro, phải có giới hạn thời gian, phải rơi về mẫu được.

## Quyết định
1. **LangGraph `StateGraph` + `AsyncPostgresSaver`**, ghi checkpoint **đồng bộ** (`durability="sync"`) sau mỗi bước.
   Thread id = id sự cố. Chờ người dùng bằng `interrupt()`; tiếp tục bằng `Command(resume=…)`.
2. **Mọi tác dụng phụ đi qua hàng đợi job Postgres** (`jobs`, `FOR UPDATE SKIP LOCKED`), có **khóa chống trùng**
   `idempotency_key = "<sự cố>:<loại>:<tên>"`. Lý do: LangGraph chạy lại node từ đầu khi resume, và node có thể chạy lại
   sau kill -9.
3. **Bộ hẹn giờ là job `graph_resume`** đặt mốc tuyệt đối khi node chạy lần đầu (khóa giữ nguyên mốc), đến hạn thì
   resume đồ thị với `expect=<node>`. Đồ thị đã đi tiếp ⇒ bỏ qua. Mỗi thread có một `pg_advisory_lock`: nút bấm của
   người giám hộ và bộ hẹn giờ không chạy chồng lên nhau.
4. **Phục hồi**: `agent_runs.status = running` trong lúc chạy (kể cả lượt resume). Khi khởi động, `recover()` chạy tiếp
   từ checkpoint cuối. Run chưa kịp có checkpoint thì đánh dấu `failed`.
5. **`llm_router` là cổng LLM duy nhất**:
   - Che PII trước, rồi bọc nội dung bên ngoài trong `<untrusted>` ở lượt user (không bao giờ đưa vào system prompt).
   - Trần cứng **4 s**, **không thử lại**. Output có cấu trúc (Pydantic, `messages.parse`).
   - Tính chi phí theo bảng giá, có trần chi tiêu mỗi ngày.
   - Lỗi, quá hạn, từ chối, hết ngân sách hay không có khóa ⇒ dùng mẫu soạn sẵn. Node ghi `agent_steps`.
   - LLM **không viết lời nói với người cao tuổi** (chỉ chọn mã câu hỏi đã duyệt). Tóm tắt cho người giám hộ nằm giữa
     mẫu có câu công khai AI; có chữ số, đường link, tên miền, @ hay tên kênh chat thì bị thay bằng câu mẫu.
   - LLM chỉ nhận siêu dữ liệu + enum; cách xưng hô thật thay bằng `{alias}`.
6. **Một cửa kiểm dữ liệu trước checkpoint** (giá trị resume được LangGraph ghi ngay vào `checkpoint_writes`):
   `start()` tra danh sách đe dọa rồi bỏ `h1` + tên gói app (ADR-006); `resume()` chỉ giữ khóa hợp lệ. **Lời kể tự
   do của người cao tuổi không bao giờ được lưu hay gửi LLM** — chỉ còn cờ tất định (`note_flags`). Tắt cứng LangSmith.
7. **Mức rủi ro chỉ nâng**: `raise_only(rule_floor, hiện tại, đề xuất LLM)` ở mọi node.
8. **`fast_alert` không dùng LLM**: tin mẫu cho người giám hộ đi ngay khi có sự cố, nên đường cảnh báo không phụ thuộc LLM.
9. **MCP Python SDK v2 (`MCPServer`)** cho `threat`, gắn tại `/mcp/threat` (stateless, JSON). Kiểm Host localhost của SDK
   chỉ chống DNS rebinding, không phải xác thực. **Cập nhật 15/10/2026 (spec 003):** `/mcp/threat` có middleware ASGI
   (`mcp_servers/auth.py`) đòi `Authorization: Bearer <token>` (máy chủ chỉ giữ SHA-256 theo tên client; chưa cấu hình
   client nào ⇒ 401) và giới hạn tần suất theo client (30/phút, 1.000/ngày, đếm trong bộ nhớ ⇒ một tiến trình, ADR-002;
   vượt ⇒ 429 + `Retry-After`) nên gắn ở mọi môi trường. Không dùng `token_verifier`/`AuthSettings` của SDK (bắt khai máy
   chủ OAuth không có, không trả được 429). **Vẫn chưa mở ra Internet** tới khi spec 012 quyết Caddy. Danh sách đe dọa nằm
   trong bảng `threat_indicators` chỉ lưu HMAC (ADR-006). Đồ thị gọi thẳng hàm miền (`lookup_h1`, async), không đi qua
   HTTP trong cùng tiến trình; tra cứu lỗi ⇒ `threat = unknown` + mã lỗi, sự cố vẫn chạy.
10. **Model hồ sơ `fast`**: cấu hình bằng `HOICON_LLM_FAST_MODEL`. Mặc định tạm thời là **Claude Haiku 5.5** (rẻ hơn Haiku
   4.5 mười lần, là thế hệ hiện tại). Chốt sau khi đo Haiku 4.5 với 5.5 (và Gemini Flash-Lite nếu cần) trên bộ eval.
   **Cập nhật 15/10/2026:** công cụ so model đã sẵn (`spike bench --model <id> --json <tệp>`, hợp đồng
   `docs/schemas/bench_report.v1.json`); **số đo model vẫn chờ khóa API (P0-08)** — không đổi quyết định mặc định. Trần
   chi tiêu/ngày nay cộng `agent_steps.cost_usd` của ngày giờ Việt Nam nên bền qua khởi động lại.

## Hệ quả
- Ba bảng mới (`jobs`, `agent_runs`, `agent_steps`, migration `0002`) cùng các bảng checkpoint của LangGraph (tạo bằng
  `setup()` khi mở runtime).
- P2-03 nối `IncidentService.transition` vào các node chuyển trạng thái, khởi động runtime + worker trong lifespan của app.
- Phải có test idempotency cho mọi node mới có tác dụng phụ. Đổi prompt ⇒ tăng `version` + `run-eval smoke`.

## Phương án đã loại
- `durability="async"` (mặc định): có thể mất checkpoint cuối khi bị kill ⇒ tác dụng phụ chạy lại.
- Hẹn giờ bằng `asyncio.sleep`/APScheduler trong tiến trình: mất khi khởi động lại; thêm thư viện (ADR-004).
- Thử lại LLM tự động: phá trần 4 s; mẫu soạn sẵn đã đủ an toàn.
- Để LLM viết thẳng tin cho người cao tuổi: rủi ro chèn lệnh, giọng gây hoảng, không kiểm được câu công khai AI.
