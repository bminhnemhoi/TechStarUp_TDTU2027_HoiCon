# HỏiCon — Hướng dẫn cho Claude Code

HỏiCon là trợ lý **Agentic AI chống lừa đảo cho cả nhà**: app Android "Lính gác" phát hiện chuỗi hành vi rủi ro
(đang nghe số lạ → mở app ngân hàng), bật **khoảng dừng an toàn** bằng giọng nói tiếng Việt, rồi 5 tác tử AI trên máy chủ
chấm rủi ro, báo con cháu qua Zalo, xác minh, lập hồ sơ vụ việc và huấn luyện. Dự thi **Tech Startup Challenger 2027**
(TDTU). Minh là người code duy nhất; bạn và các subagent là "đội chuyên gia". Báo cáo cho Minh **bằng tiếng Việt**.

Mốc cứng: nộp Vòng 1 **15/11/2026** · MVP Vòng 2 **10/01/2027** (đóng băng code 06/01) · chung kết **27/02/2027**.

## Tài liệu là nguồn sự thật (đọc trước khi làm)

| Tài liệu | Nội dung |
|---|---|
| `docs/ROADMAP.md` | Khối STATUS, mã task (P0-xx…), gate, danh sách cắt — **chỉ làm task trong đây** |
| `docs/PRD.md` | User story (US-xx), tiêu chí chấp nhận |
| `docs/ARCHITECTURE.md`, `docs/adr/` | Kiến trúc, quyết định đã chốt (ADR-001…) |
| `docs/DATA-MODEL.md`, `docs/API.md`, `docs/schemas/` | Bảng, state machine sự cố, hợp đồng API/sự kiện |
| `docs/AGENTS.md` | Đồ thị LangGraph, tác tử, công cụ MCP, router mô hình |
| `docs/DESIGN-SYSTEM.md` | Token, màn hình E1–E12, chuẩn cho người cao tuổi — **thắng mọi plugin thiết kế** |
| `docs/PRIVACY-DPIA.md`, `docs/PLAY-POLICY.md` | Quyền riêng tư, đồng ý, chính sách Google Play |
| `docs/EMULATOR.md` | Máy ảo Android, kịch bản mô phỏng cuộc gọi |
| `docs/proposal/` | Thuyết minh đã nộp — mọi cam kết phải giữ (dùng skill `pitch-sync`) |

## Stack

- **Android** (`apps/android`): Kotlin 2.4, Compose + Material 3, AGP 9.4, minSdk 29, target/compileSdk 36. Module `:app`, `:rules` (JVM thuần, luật tất định), `:demobank` (app ngân hàng giả để thử/demo). Gradle chạy bằng JDK 21 (`D:/Android/jdk-21`), SDK ở `D:/Android/Sdk`.
- **Backend** (`backend/`, một dự án `uv`, Python 3.12): FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, psycopg 3, LangGraph (`AsyncPostgresSaver`), FastMCP gắn tại `/mcp/*`, hàng đợi job bằng Postgres. **Đọc skill `claude-api` trước khi viết code gọi Claude/Anthropic SDK.**
- **Web** (`apps/web`): Next.js, Tailwind v4, shadcn/ui, client TS sinh từ OpenAPI.
- **Hạ tầng**: `infra/compose.dev.yml` — Postgres pgvector **cổng 15432**; API **18000**; web **3100** (các cổng 5432/6379/8000/3000 thuộc dự án khác).
- **Kênh người giám hộ**: Zalo Bot Platform (giới hạn 3 bot × 50 người, 3.000 tin/tháng).

## Lệnh

```bash
docker compose -f infra/compose.dev.yml up -d        # Postgres 15432
uv run --directory backend alembic upgrade head
uv run --directory backend uvicorn hoicon.api.main:app --port 18000 --reload --loop asyncio:SelectorEventLoop  # Windows: psycopg async
uv run --directory backend pytest                       # unit + integration + graph
pnpm --dir apps/web dev                                 # http://localhost:3100
apps/android/gradlew -p apps/android :rules:test :app:assembleDebug
python scripts/emu-scenario.py --avd hc-api36 --scenario fake_police   # E2E trên máy ảo
```

Chạy CLI bằng **tool Bash** (để RTK nén output). Cần output đầy đủ khi debug: `rtk run <lệnh>`.

## Luật bắt buộc

### Quyền riêng tư & an toàn (không ngoại lệ)
1. **Không bao giờ log, lưu, in, hay gửi cho LLM** số điện thoại, số tài khoản, tên thật, Zalo ID, OTP, CCCD ở dạng thô.
   Backend dùng `hoicon.domain.pii` (mask/hash), Android dùng `PiiMasker`. Hook `guard-privacy` chặn số điện thoại thô trong mã nguồn.
2. Thiết bị chỉ gửi `h1 = SHA-256("hoicon:v1:"+E164)`; máy chủ chỉ lưu `HMAC(pepper[kid], h1)` + 3 số cuối. Fixture chỉ dùng số hư cấu, đặt trong `tests/` hoặc `data/`.
3. **Android cấm**: quyền SMS, nhật ký cuộc gọi, danh bạ (dùng contact picker), `QUERY_ALL_PACKAGES`, `REQUEST_INSTALL_PACKAGES`, Accessibility, Notification Listener, ghi âm cuộc gọi; không tự động thao tác app khác. Chỉ luật **tất định** trên máy.
4. **Đường dừng an toàn không dùng mạng hay LLM**, phải hiện ≤ 3 giây kể cả khi offline. Không bao giờ chặn vĩnh viễn: nút "tiếp tục" cần giữ 3 giây, kết quả được ghi lại.
5. LLM chỉ được **nâng** mức rủi ro, không bao giờ hạ dưới mức sàn của luật trên máy. Mọi lời gọi LLM đi qua `llm_router` (che PII, ngân sách, timeout ≤ 4 s, trace, output có cấu trúc, rơi về mẫu soạn sẵn). Văn bản do kẻ gian cung cấp bọc `<untrusted>`, không đưa vào system prompt. Công cụ có tác dụng phụ (gửi Zalo, đẩy thông báo) chỉ được gọi từ node trong danh sách cho phép.
6. **Công khai AI**: tin đầu tiên tới người cao tuổi và mọi tin Zalo trong một sự cố mở đầu bằng "Đây là trợ lý AI HỏiCon" (có test).
7. Mục đích dữ liệu mới ⇒ thêm giá trị enum đồng ý + phiên bản văn bản (skill `consent-copy`). Bảng `consents` chỉ ghi thêm.
8. Diễn tập: cờ `is_drill` ở mọi nơi, tên cơ quan và số điện thoại hư cấu, debrief sau đó, không bao giờ báo như sự cố thật. Dữ liệu demo hư cấu, cờ `is_demo`. Thí điểm chỉ người ≥ 18 tuổi.
9. Gửi Zalo chỉ qua bộ kiểm hạn mức (`messages_out`). Không đọc `.env`, keystore, `D:/secrets`.

### Code
10. **Hợp đồng trước**: JSON Schema + fixture dùng chung trong `docs/schemas/`; đổi API ⇒ sinh lại client TS.
11. Mọi chuyển trạng thái sự cố đi qua `IncidentService.transition()` (skill `state-transition`). Migration Alembic đã lên `main` là bất biến.
12. Viết ít code nhất đủ dùng (tinh thần ponytail: tái dùng cái có sẵn, tính năng native, không over-engineer) — nhưng **không bao giờ** cắt kiểm tra hợp lệ, xử lý lỗi, khả năng tiếp cận, quyền riêng tư, hay trạng thái loading/empty/error.
13. Code và định danh bằng tiếng Anh; mọi chữ người dùng nhìn thấy bằng tiếng Việt (giọng ấm áp, không gây hoảng sợ, có hành động cụ thể).
14. Python: type hints, `ruff`; Kotlin: không `!!` ở code sản phẩm; TS: `strict`. Không thêm thư viện khi chưa nêu lý do.

### UI
15. App người cao tuổi: chữ ≥ 20sp, nút chính ≥ 24sp đậm, vùng chạm ≥ 64dp, ≤ 2 hành động chính/màn, tương phản ≥ 7:1, dùng được ở cỡ chữ 200%, màn quan trọng tự đọc to. Màu rủi ro luôn đi kèm biểu tượng + chữ. Diễn tập dùng màu riêng.
16. Mọi màn hình mới dùng skill `ui-screen` và được `ux-elder-reviewer` (app) hoặc screenshot Playwright (web) kiểm tra.

## Definition of Done (mỗi task)
- Test xanh ở mọi tầng bị đụng tới; agent/prompt đổi ⇒ `run-eval smoke` đạt.
- Code cảm biến Android đổi ⇒ chạy `emu-scenario.py` trên AVD API 36 và 34.
- UI đổi ⇒ đã xem screenshot. Docs liên quan đã cập nhật. `privacy-audit` sạch nếu đụng dữ liệu cá nhân.
- Cập nhật trạng thái task trong `docs/ROADMAP.md`.

## Quy trình làm việc
1. Đọc STATUS (SessionStart hiện sẵn), chọn **một** task. Việc lớn: vào Plan mode, hỏi đúng chuyên gia (`android-engineer`, `agent-architect`, `backend-db`, `web-ux`).
2. Làm theo skill `feature-slice` (hợp đồng → DB → domain → API → Android/web → test → docs).
3. Review: `security-privacy-reviewer` (dữ liệu cá nhân/LLM/manifest/Zalo), `ux-elder-reviewer` (màn hình, câu chữ), `/ponytail-review`.
4. **Chỉ commit khi Minh yêu cầu**; nhánh `feat/<task-id>-<slug>`, PR qua `gh`. Cuối tuần chạy `phase-gate`.
5. Workflow/đa tác tử song song chỉ dùng khi Minh yêu cầu rõ. Tối đa 2 worktree (android / phần còn lại).

## Kiểm soát phạm vi
- Ý tưởng ngoài task ⇒ ghi vào mục "Ghi chú" của ROADMAP, không làm.
- Gate trễ > 2 ngày ⇒ cắt mục kế tiếp trong danh sách cắt, không kéo dài phase.
- **Không bao giờ cắt**: sổ đồng ý, công khai AI, che PII, dừng an toàn, đường cảnh báo, trace, eval ≥ 100 ca.
- Không tuyên bố số liệu/tương thích chưa đo được (máy ảo ≠ máy thật; ghi rõ nguồn số liệu).
