# Kiến trúc HỏiCon

> Quyết định đã chốt nằm trong `docs/adr/`. File này mô tả tổng thể; chi tiết bảng ở `DATA-MODEL.md`, hợp đồng API ở
> `API.md` + `docs/schemas/`, đồ thị tác tử ở `AGENTS.md`.

## 1. Nguyên tắc thiết kế

1. **Đường găng không phụ thuộc mạng hay LLM.** Phát hiện → dừng an toàn chạy hoàn toàn trên máy bằng luật tất định
   (ADR-001), ≤ 3 giây, kể cả offline. Máy chủ và LLM chỉ làm phần "sau đó": hỏi lại, báo con cháu, xác minh, hồ sơ.
2. **LLM chỉ được nâng rủi ro.** Mức can thiệp cuối cùng ≥ `rule_floor` do máy gửi lên. LLM quá hạn ⇒ mẫu soạn sẵn.
3. **Riêng tư theo thiết kế.** Không đọc SMS / nhật ký cuộc gọi / danh bạ / nội dung cuộc gọi; số điện thoại chỉ đi
   dưới dạng băm (ADR-006); che PII trước mọi lời gọi LLM; sổ đồng ý chỉ ghi thêm.
4. **Ít thành phần nhất.** Một tiến trình FastAPI chứa API + LangGraph + MCP (ADR-002); Postgres làm luôn hàng đợi job,
   checkpoint, vector (ADR-004). Không Redis, không Kafka, không Kubernetes.
5. **Con người quyết định.** Người cao tuổi luôn tiếp tục được (giữ 3 s); người giám hộ duyệt hồ sơ vụ việc trước khi gửi.

## 2. Sơ đồ thành phần

```
┌──────────── Điện thoại người cao tuổi (Android 10–16) ────────────┐
│ :app "Lính gác"                                                    │
│  CallScreeningService ──► RiskWindow (FGS specialUse, ≤10')        │
│  UsageStats poll 1s ────► :rules (JVM thuần: R0–R4, rule_floor)     │
│        │ high/critical                                             │
│        ▼                                                           │
│  SafePauseActivity (TTS/âm thanh thu sẵn, offline) ◄── KHÔNG mạng   │
│        │ sự kiện (chỉ siêu dữ liệu, h1)                             │
│  Room outbox ──(HTTPS, gửi lại an toàn)──────────────┐              │
│  FCM ◄── câu hỏi E8 / kết quả                        │              │
└──────────────────────────────────────────────────────┼──────────────┘
                                                       ▼
┌──────────────── Máy chủ (VPS, docker compose + Caddy) ───────────────┐
│ FastAPI (uvicorn, :18000)                                            │
│  /v1 API ─► IncidentService (state machine, advisory lock)           │
│  LangGraph (AsyncPostgresSaver) ─► llm_router (fast/strong/judge)    │
│  /mcp/{threat,zalo,scenario,docs,voice} (FastMCP)                    │
│  job worker (Postgres FOR UPDATE SKIP LOCKED): hẹn giờ T1/T2/T3,     │
│      gửi Zalo qua bộ kiểm hạn mức, xóa theo hạn lưu                  │
│  SSE: runs/{id}/stream, families/{id}/stream, demo/stream            │
│ Postgres 17 + pgvector (:15432 dev)                                  │
└───────┬───────────────────────────────┬──────────────────────────────┘
        ▼                               ▼
  Zalo Bot Platform               Web Next.js (:3100)
  (người giám hộ: Z1–Z8)          /a/[token], /f/[id], /trace, /eval, /sim, /booth
```

## 3. Android "Lính gác" (`apps/android`)

| Module | Nội dung | Phụ thuộc |
|---|---|---|
| `:rules` | Máy trạng thái rủi ro, chấm điểm R0–R4, chuẩn hóa E.164 + `h1`, khớp danh sách đe dọa (hash), `rule_floor` | Kotlin/JVM thuần — test hàng trăm ca trong vài giây, chạy trong CI không cần máy ảo |
| `:app` | UI Compose (E1–E12), dịch vụ, Room (`sentinel.db`), DataStore + Tink, mạng (outbox), FCM, TTS | `:rules` |
| `:demobank` | App "Ngân hàng Mẫu" để thử trên máy ảo và demo ở gian (app ngân hàng thật thường chặn máy ảo) | — |

**Cơ chế cảm biến** (đã kiểm chứng ở P1-S1):
- `CallScreeningService` (vai trò `CALL_SCREENING`): biết có cuộc gọi đến, số có trong danh bạ hay không
  (`Call.Details`), gắn nhãn số bị gắn cờ — **không cần** `READ_CALL_LOG`.
- Trạng thái cuộc gọi: `TelephonyCallback` (cần `READ_PHONE_STATE`) hoặc `AudioManager.mode` — chọn ở P1-S1.
- Cửa sổ rủi ro: foreground service `specialUse` khi đang gọi hoặc ≤ 10 phút sau cuộc gọi số lạ; trong cửa sổ quét
  `UsageStatsManager` mỗi 1 s để biết app ngân hàng/ví (`data/bank_apps.vn.json`) lên tiền cảnh.
- `SafePauseActivity` toàn màn hình, mở nhờ quyền "hiển thị trên ứng dụng khác" (miễn trừ giới hạn khởi chạy nền).
  **Không vẽ đè lên app ngân hàng**; nút "tiếp tục" giữ 3 s; không bao giờ chặn vĩnh viễn.
- Cấm: SMS, nhật ký cuộc gọi, danh bạ (dùng contact picker), `QUERY_ALL_PACKAGES` (khai báo `<queries>` cho các gói
  ngân hàng), `REQUEST_INSTALL_PACKAGES`, Accessibility, Notification Listener, ghi âm — hook `guard-privacy` chặn.

**Ngân sách độ trễ đường găng (mục tiêu p95 ≤ 3 s):** app ngân hàng lên tiền cảnh → phát hiện ≤ 1,2 s (chu kỳ quét 1 s)
→ quyết định luật ≤ 50 ms → mở SafePause ≤ 800 ms → câu nói đầu tiên ≤ 500 ms. Đo bằng logcat tag `HC_TIMING`.

## 4. Backend (`backend/`, một dự án `uv`, Python 3.12)

```
backend/src/hoicon/
  api/            FastAPI routers (/v1, /webhooks/zalo, /demo, /admin), deps, auth (device JWT, action token)
  domain/         incident state machine, rule_floor, pii (mask/hash/HMAC), consent purposes, schemas (Pydantic)
  db/             SQLAlchemy models, session, repositories
  agents/         graphs/ (incident, coach), nodes/, prompts/*.md (có phiên bản), llm_router.py, question_bank
  mcp_servers/    threat, zalo, scenario, docs, voice (FastMCP, gắn tại /mcp/*)
  integrations/   zalo, llm (anthropic, gemini), stt/tts, fcm
  jobs/           worker, timers (T1/T2/T3), retention, quota
  evalkit/        CLI hoicon-eval (P2-15)
backend/migrations/   Alembic (bất biến khi đã lên main)
backend/tests/        unit/ integration/ graph/ contract/
```

- **Một tiến trình** (ADR-002): API, LangGraph và MCP cùng event loop; worker job là một task nền trong cùng tiến trình
  ở dev, có thể tách thành tiến trình riêng ở prod bằng cùng mã (`hoicon worker`).
- **LangGraph**: checkpoint `AsyncPostgresSaver` (psycopg 3) ⇒ chạy tiếp được sau khi tiến trình chết; interrupt cho
  `ask_elder`, `await_guardian`, `await_case_approval`; hẹn giờ là job trong Postgres, khi đến hạn thì `Command(resume=…)`.
- **`llm_router`**: hồ sơ `fast` (Haiku 4.5 / Gemini Flash-Lite), `strong` (Sonnet 5.5 / Gemini Pro), `judge` (khác
  nhà cung cấp bên sinh). Mỗi lời gọi: che PII → bọc `<untrusted>` → timeout ≤ 4 s → output có cấu trúc → ghi
  `agent_steps` → rơi về mẫu. Đổi nhà cung cấp qua biến môi trường. **Đọc skill `claude-api` trước khi viết mã SDK.**
- **Zalo** (ADR-003): webhook `POST /webhooks/zalo/{bot_id}` kiểm secret, chống trùng, trả 200 ngay, xử lý trong job.
  Mọi tin gửi đi qua `messages_out` (bộ đếm hạn mức theo bot: cảnh báo 80%, dừng bản tin ở 95%).

## 5. Web (`apps/web`, Next.js + Tailwind v4 + shadcn/ui)

Client TS sinh từ OpenAPI (`openapi-typescript`, `scripts/gen-api-client.sh`). Trang: công khai (`/`, `/privacy`, `/ai`),
người giám hộ (`/a/[token]` trang hành động trên điện thoại, `/f/[id]`, `/incidents/[id]`), kỹ thuật/giám khảo
(`/trace/[runId]` dùng xyflow, `/eval`, `/sim` điện thoại mô phỏng), gian (`/booth`, `/join/[code]`, `/demo/console`).

## 6. Môi trường & cổng

| Thành phần | Dev (máy Minh) | Prod / thí điểm |
|---|---|---|
| Postgres 17 + pgvector | `infra/compose.dev.yml`, cổng **15432** | `compose.prod.yml`, chỉ mạng nội bộ |
| API | `uvicorn … --port 18000` | sau Caddy (HTTPS) |
| Web | `pnpm --dir apps/web dev` cổng **3100** | build tĩnh/Node sau Caddy |
| Webhook Zalo | cloudflared tunnel → 18000 | tên miền thật |
| Android | AVD `hc-api36/34/29` (`docs/EMULATOR.md`) | Play internal/closed testing (ADR-005) |

Cổng 5432/6379/8000/3000/54321–54327 thuộc dự án khác trên máy dev — không dùng.

## 7. Quan sát & vận hành

- Trace: bảng `agent_steps` (đã che PII) + SSE → `/trace/[runId]`. Langfuse là tùy chọn (nằm trong danh sách cắt).
- Android: heartbeat (trạng thái quyền, phiên bản luật/danh sách) → phát hiện "mất bảo vệ"; Crashlytics từ P2-20.
- Hạn lưu: sự kiện 90 ngày · nội dung bước tác tử 30 ngày · sự cố 12 tháng · demo 24 giờ (job `retention`).

## 8. Giới hạn đã biết

- Máy ảo không tái hiện việc Xiaomi/Oppo/Samsung diệt tác vụ nền; app ngân hàng VN thật thường từ chối máy ảo ⇒
  thiết kế phòng thủ (FGS trong cửa sổ rủi ro, heartbeat, thông báo dự phòng sau cuộc gọi), Firebase Test Lab trước M2,
  máy của gia đình thí điểm. Không tuyên bố tương thích hãng nào chưa thử.
- Zalo Bot Platform: hạn mức và điều khoản có thể đổi ⇒ trang hành động web + web push là đường dự phòng.
