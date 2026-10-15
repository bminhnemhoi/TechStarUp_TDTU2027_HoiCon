# Bàn giao HỏiCon — đọc file này trước tiên

> Cập nhật **14/10/2026** · Chủ dự án: **Ngô Bình Minh** ([@bminhnemhoi](https://github.com/bminhnemhoi)) · Đồng phát triển
> từ 14/10/2026: **Ngô Lâm Tiến** ([@Towfienes](https://github.com/Towfienes), collaborator — lời mời gửi 14/10, chấp nhận
> trong 7 ngày tại https://github.com/bminhnemhoi/TechStarUp_TDTU2027_HoiCon/invitations).
> Mục đích: ai cầm repo này cũng làm tiếp được kế hoạch mà không cần hỏi lại, kể cả khi Minh tạm vắng.
> Nguồn sự thật về "làm gì tiếp" vẫn là [`docs/ROADMAP.md`](ROADMAP.md); file này là bản đồ + hướng dẫn + kế hoạch gần.
> Từ 15/10/2026: kế hoạch tới 100% phạm vi theo Spec Kit (danh mục spec, phụ thuộc, worktree) ở [`docs/MASTER-PLAN.md`](MASTER-PLAN.md).

## 0. Tóm tắt 1 phút

- **HỏiCon** là trợ lý Agentic AI chống lừa đảo cho người cao tuổi, dự thi **Tech Startup Challenger 2027** (Khoa CNTT – TDTU).
  - App Android **"Lính gác"** nhận ra chuỗi *đang nghe số lạ → mở app ngân hàng* bằng luật tất định trên máy, rồi hiện
    màn **"Khoan chuyển tiền đã"** có giọng nói trong ≤ 3 giây, kể cả khi mất mạng.
  - Máy chủ (FastAPI + LangGraph) chấm rủi ro, hỏi lại người cao tuổi, báo con cháu qua Zalo, nhắc lại và chuyển người
    thân thứ hai nếu im lặng.
- **Mốc cứng**: nộp Vòng 1 **13/11/2026** (hạn 15/11) · MVP Vòng 2 **09/01/2027** (đóng băng code 06/01) · chung kết **27/02/2027**.
- **Tiến độ ước tính**:
  - ≈ 15% tổng thể; ≈ 30% hồ sơ Vòng 1.
  - Phần kỹ thuật đi trước lịch: spike S1, S2, S4 có code chạy được + báo cáo + ADR.
  - Phần hồ sơ (thuyết minh, video, khảo sát 300 phản hồi) chưa bắt đầu ⇒ ưu tiên số 1 của 3 tuần tới (§5).
- **Chưa làm được vì thiếu tài khoản** (Minh đang đăng ký): Firebase (đo trên máy thật), Zalo Bot, Anthropic/Gemini API,
  Google Play Console.

## 1. Mốc thời gian và đầu ra phải nộp

| Mốc | Ngày | Phải có |
|---|---|---|
| Gate G1 | 08/11/2026 | 5 báo cáo spike trong `docs/spikes/` (có số đo, kết luận đi tiếp/không), ADR-007…010, video xong |
| **Nộp Vòng 1** | **13/11/2026** | thuyết minh cập nhật (Word + PDF) + video 3 phút + số liệu khảo sát |
| Gate M1 | 06/12/2026 | luồng cảnh báo đầu–cuối trên máy ảo API 34 + 36 |
| Gate M2 | 20/12/2026 | ≥ 5 gia đình đã cài, ≥ 1 máy thật |
| **Nộp Vòng 2** | **09/01/2027** | MVP + báo cáo thí điểm + poster + video 5 phút; eval ≥ 100 ca |
| **Chung kết** | **27/02/2027** | gian trưng bày chạy ổn định, slide 10 phút; bình chọn tại gian chiếm 30% |

Thể lệ cuộc thi: [`docs/competition/The_le_Tech_Startup_Challenger_2027.pdf`](competition/The_le_Tech_Startup_Challenger_2027.pdf).
Thuyết minh đã nộp: [`docs/proposal/`](proposal/). Mọi cam kết trong đó phải giữ; kiểm bằng skill `pitch-sync`.

## 2. Trạng thái hiện tại (14/10/2026)

### Đã xong và chạy được

| Phần | Kết quả | Tài liệu |
|---|---|---|
| Nền móng P0 | Monorepo, CI 5 workflow (backend, android, web, harness, gitleaks), harness Claude Code (7 hook, 8 subagent, 8 skill) | [G0](phase-reports/G0.md), [HARNESS](HARNESS.md) |
| P1-S1 Cảm biến Android | `CallScreeningService` (chỉ quan sát) → cửa sổ rủi ro (FGS) → UsageStats → `SafePauseActivity`. Trên máy ảo: bắt 10/10 cuộc gọi, chạy offline được, không cần `READ_PHONE_STATE` | [spike](spikes/P1-S1-cam-bien.md), [ADR-007](adr/ADR-007-co-che-cam-bien-android.md) |
| P1-S2 Dừng an toàn + app ngân hàng | Danh sách 50 app tài chính (sinh tự động ra code, có test chống lệch). `:demobank` có luồng chuyển tiền giả. Bộ đo `:latency` sẵn sàng cho Firebase Test Lab. Kết luận về full-screen intent và Thông tư 77/2025 | [spike](spikes/P1-S2-dung-an-toan.md), [ADR-008](adr/ADR-008-dung-an-toan-va-app-ngan-hang.md) |
| P1-S4 Lõi tác tử | Đồ thị LangGraph 2 interrupt + hẹn giờ T1/T2/T3 bằng job Postgres. Chạy tiếp sau kill -9 (có test). Cổng LLM duy nhất (trần 4 s, chỉ nâng mức rủi ro, rơi về mẫu). MCP `threat`. Trace `agent_steps`. 86 test backend xanh | [spike](spikes/P1-S4-loi-tac-tu.md), [ADR-009](adr/ADR-009-loi-tac-tu.md) |
| P1-07 Kịch bản lừa đảo | Bản nháp 60 ca (40 lừa đảo / 20 hợp lệ / 10 chèn lệnh), schema + test hợp đồng. **Chờ Minh duyệt** (`draft: true`) | [EVAL](EVAL.md), `data/scenarios/` |
| P1-02 Bảng hỏi khảo sát | Bảng hỏi v1 xong; **chưa dựng Google Form, chưa phát tán** | [bảng hỏi](research/survey/P1-02-bang-hoi.md) |

### Đang dở / chờ

| Việc | Còn thiếu | Chặn bởi |
|---|---|---|
| P1-S1/S2 số đo máy thật | p95 "mở app ngân hàng → màn dừng" ≤ 3 s trên **máy thật**; số máy ảo bị thổi phồng | tài khoản Firebase (P0-08) |
| P1-S2 phần máy ảo | ảnh `:demobank` cho `ux-elder-reviewer`, kiểm full-screen intent trên AVD 34/36 | máy dev của Minh hết RAM, ổ C đầy |
| P1-S4 chọn model | đo Haiku 4.5 với Haiku 5.5 (mặc định tạm) — độ trễ, chi phí, chất lượng | khóa Anthropic |
| P1-S3 Zalo Bot, P1-S5 giọng nói | chưa bắt đầu | token Zalo; khóa STT/TTS (hoặc chỉ dùng `SpeechRecognizer` trên máy) |
| P1-01 thuyết minh, P1-03 video, P1-04 nộp | chưa bắt đầu | — (ưu tiên số 1) |
| P1-05 design system, P1-06 đồng ý + DPIA, P1-08 Play internal, P1-09 VPS | chưa bắt đầu | P1-08 cần Play Console |

### Pull request

- PR tổng hợp **"Bàn giao 14/10"** gộp P1-S2 + P1-S4 + P1-07 + tài liệu này. Thay cho #6, #7, #8 (đã đóng, trỏ về PR tổng hợp).
- Dependabot #5 (nâng phiên bản GitHub Actions) còn mở; merge được nếu CI xanh.

## 3. Ngày đầu tiên: dựng môi trường

### 3.1 Công cụ

| Công cụ | Phiên bản | Ghi chú |
|---|---|---|
| Git + GitHub CLI `gh` | mới nhất | `gh auth login` |
| Docker Desktop | mới nhất | Postgres 17 + pgvector chạy trong container `hoicon-db` |
| Python | 3.12 qua **uv** | `pip install uv` hoặc xem astral.sh/uv |
| Node.js + **pnpm** | Node ≥ 22, pnpm 12 | `corepack enable` |
| JDK 21 + Android SDK (compileSdk 36) | | `bash scripts/setup-android.sh` (Windows: `D:/Android`; Linux/macOS: `~/Android`; đổi bằng `ANDROID_ROOT`) — xem `EMULATOR.md` §1. Có thể dùng Android Studio |
| (tùy chọn) Claude Code | mới nhất | §4.3 |

**Cổng cố định** (máy Minh có dự án khác chiếm 5432/6379/8000/3000): Postgres **15432**, API **18000**, web **3100**.

### 3.2 Chạy thử từng tầng

```bash
git clone https://github.com/bminhnemhoi/TechStarUp_TDTU2027_HoiCon.git && cd TechStarUp_TDTU2027_HoiCon
pnpm install
uv sync --directory backend

# Backend
docker compose -f infra/compose.dev.yml up -d            # Postgres 127.0.0.1:15432
uv run --directory backend alembic upgrade head
uv run --directory backend pytest                         # ~86 test; integration tự bỏ qua nếu DB tắt
uv run --directory backend python -m hoicon.agents.spike demo   # một sự cố đầu–cuối (không có khóa ⇒ LLM rơi về mẫu)

# API + web
pnpm dev:all                                              # DB → migration → API :18000 + web :3100

# Android (Git Bash; đặt JAVA_HOME tới JDK 21)
apps/android/gradlew -p apps/android :rules:test :app:assembleDebug :demobank:assembleDebug
```

- Máy ảo, cấp quyền bằng adb, mô phỏng cuộc gọi: [`EMULATOR.md`](EMULATOR.md) và [`apps/android/README.md`](../apps/android/README.md).
- **Windows**: psycopg async cần `SelectorEventLoop`. Lệnh uvicorn trong `package.json` đã kèm `--loop asyncio:SelectorEventLoop`;
  test và Alembic tự xử lý.

### 3.3 Bí mật (không bao giờ commit)

- `uv run --directory backend python -m hoicon.ops.init_env` tạo `backend/.env`. Lệnh tự sinh pepper băm số điện thoại +
  secret webhook và để chỗ trống cho khóa dán tay.
- `uv run --directory backend python -m hoicon.ops.check_keys` kiểm tra từng khóa, chỉ in Đạt/Thiếu/Lỗi.
- Biến môi trường tiền tố `HOICON_`, xem [`backend/.env.example`](../backend/.env.example). Repo **public**; gitleaks chạy
  trên mọi PR.
- **Pepper** (`HOICON_PHONE_PEPPER_1`) mất là không so khớp lại được số đã băm. Mỗi môi trường (dev từng người, VPS) có
  pepper riêng; bản prod do Minh giữ.

## 4. Cách làm việc

### 4.1 Quy trình một task

1. Chọn **một** task trong [`ROADMAP.md`](ROADMAP.md), đổi trạng thái sang `◐`, cập nhật khối `<!-- STATUS -->` (≤ 6 dòng).
2. Tạo nhánh `feat/<mã-task>-<slug>`, ví dụ `feat/p1-s3-zalo`. Không push thẳng vào `main`.
3. Làm theo lát dọc: hợp đồng JSON Schema (`docs/schemas/`) → migration → domain → API → tác tử → Android/web → test → docs
   (skill `feature-slice`).
4. Mở PR (có mẫu checklist). CI phải xanh. **Người còn lại duyệt** rồi *Squash and merge* + xóa nhánh.
5. Cập nhật ROADMAP (`☑`, kèm ghi chú bằng chứng) và tài liệu liên quan trong cùng PR.

**Definition of Done**:
- test xanh ở mọi tầng bị đụng tới;
- đổi prompt/đồ thị ⇒ chạy eval;
- đổi code cảm biến ⇒ chạy kịch bản trên AVD API 36 + 34;
- đổi UI ⇒ có ảnh chụp;
- đụng dữ liệu cá nhân ⇒ review quyền riêng tư;
- ROADMAP đã cập nhật.

### 4.2 Luật không được phá (tóm tắt [`CLAUDE.md`](../CLAUDE.md))

1. Không log, lưu, gửi LLM số điện thoại, số tài khoản, tên thật, Zalo ID, OTP, CCCD ở dạng thô.
   - Máy gửi `h1 = SHA-256("hoicon:v1:"+E164)`.
   - Máy chủ lưu `HMAC(pepper, h1)` + 3 số cuối.
   - Backend dùng `hoicon.domain.pii`.
   - Lời kể tự do của người cao tuổi **không lưu**, chỉ giữ cờ (ADR-009).
2. Android **cấm**: SMS, nhật ký cuộc gọi, danh bạ, `QUERY_ALL_PACKAGES`, Accessibility, Notification Listener, ghi âm
   cuộc gọi. Hook `guard-privacy` + CI chặn.
3. Màn dừng an toàn **không dùng mạng hay LLM**, hiện ≤ 3 s, không bao giờ chặn vĩnh viễn (giữ 3 giây để tiếp tục).
4. LLM chỉ được **nâng** mức rủi ro. Mọi lời gọi LLM đi qua `agents/llm_router.py`. Nội dung từ bên ngoài bọc `<untrusted>`.
5. Mọi tin tới người cao tuổi/người giám hộ mở đầu bằng **"Đây là trợ lý AI HỏiCon"** (có test). Diễn tập có nhãn
   `[DIỄN TẬP]` + cờ `is_drill`.
6. Dữ liệu demo và fixture chỉ dùng số **hư cấu** dải `0900000xxx` (`data/fixtures/phones.json`). Không gọi, nhắn hay
   diễn tập trên số này.
7. **Chặn phát hành**: chưa đưa bản build cho người thật khi chưa có P2-02 (công bố + sổ đồng ý), P2-05 (Room + Tink) và
   P1-08 (bản release qua Play). Chỉ phát hành qua Google Play, không gửi APK (ADR-005, ADR-008).
8. Code + định danh tiếng Anh; chữ người dùng thấy bằng tiếng Việt, giọng ấm áp, xưng "bác", không gây hoảng sợ.
9. Viết ít code nhất đủ dùng, nhưng không cắt kiểm tra hợp lệ, xử lý lỗi, khả năng tiếp cận, quyền riêng tư.

### 4.3 Làm cùng Claude Code (khuyến nghị)

- Mở repo bằng Claude Code. Hook `SessionStart` tự hiện đếm ngược + khối STATUS + task kế tiếp. `CLAUDE.md` nạp sẵn luật.
- Cài plugin + RTK: `bash scripts/setup-claude-tools.sh` (đọc trước), rồi `--install`. Chi tiết: [`HARNESS.md`](HARNESS.md).
- Subagent chuyên gia (`.claude/agents/`): `android-engineer`, `agent-architect`, `backend-db`, `web-ux`, `qa-eval`,
  `security-privacy-reviewer`, `ux-elder-reviewer`, `judge`. Gọi reviewer bảo mật sau mọi thay đổi chạm dữ liệu cá nhân,
  LLM, manifest, Zalo — hai lần review gần nhất đều bắt được lỗi thật.
- Skill (`.claude/skills/`): `feature-slice`, `android-emulator-test`, `add-scam-scenario`, `run-eval`, `privacy-audit`,
  `ui-screen`, `pitch-sync`, `phase-gate`.
- **Hook sẽ chặn** (đúng thiết kế): đọc `.env`/keystore, push vào `main`, `rm -rf` ngoài thư mục build, số điện thoại
  thô trong mã nguồn. Khi bị chặn: đọc thông báo, sửa cách làm, không tìm cách lách.
- **Ghi chú cho Claude ở máy mới:** memory cục bộ của máy Minh không đi theo repo; mọi điều cần biết đã chép vào file này.

### 4.4 Không dùng Claude Code

Mọi thứ chạy bằng lệnh thường (§3.2). Đọc `CLAUDE.md` như quy ước nhóm. Trước khi mở PR, tự chạy:
- `uv run --directory backend ruff check . && uv run --directory backend ruff format --check .`
- `pytest`
- `gradlew :rules:test`
- `node --test ".claude/hooks/test/*.test.mjs"`

## 5. Kế hoạch tiếp theo

**Ký hiệu người làm:** M = Minh, T = Tiến, C = Claude Code. Ai rảnh thì nhận, ghi tên vào ROADMAP.

### 5.1 Tuần 15–21/10 — gỡ chặn

| # | Việc | Ai | Xong khi |
|---|---|---|---|
| 1 | Merge PR tổng hợp; xóa worktree cũ `D:/hoicon-wt-backend` trên máy Minh | M | `main` có P1-S2, P1-S4, P1-07 |
| 2 | **P0-08 tài khoản**: Firebase (Spark) → mời T vào project; Google Play Console (25 USD, xác minh danh tính, cần một máy Android thật để bấm Verify); Zalo Bot `hoicon-dev`; Anthropic (trần 10–20 USD); Gemini. Từng bước: [`setup/ACCOUNTS.md`](setup/ACCOUNTS.md) | M | `check_keys` báo Đạt; T có quyền trong Firebase/Play/Anthropic workspace |
| 3 | Dựng Google Form từ bảng hỏi P1-02 và phát tán (nhóm Zalo gia đình, lớp, câu lạc bộ người cao tuổi) | M + T | ≥ 100 phản hồi trước 28/10, ≥ 300 trước 08/11 |
| 4 | Máy chạy được máy ảo Android: dọn ổ C máy Minh (an toàn nhất: xóa cache uv/npm/pnpm, chuyển pagefile và ổ ảo Docker sang D:) hoặc dùng máy của T (≥ 16 GB RAM, ≥ 30 GB trống) | M/T | chạy được AVD `hc-api36` |
| 5 | Duyệt 60 kịch bản trong `data/scenarios/`, sửa trực tiếp file YAML, đổi `draft: false` | M | `pytest tests/contract/test_scenarios.py` xanh |

### 5.2 Tuần 22/10–08/11 — spike còn lại + hồ sơ

| # | Việc | Ai | Xong khi |
|---|---|---|---|
| 6 | **Đo máy thật**: `bash scripts/ftl-latency.sh model=…,version=…` trên ≥ 2 máy (1 Samsung dòng A, 1 Pixel) | T | có số trong `docs/spikes/device-matrix.md` + đóng phần "chưa chốt" ở ADR-007 |
| 7 | **P1-S3 Zalo Bot**: webhook `POST /webhooks/zalo/{bot_id}` qua cloudflared (kiểm secret, chống trùng, trả 200 ngay, xử lý trong job) → `/start <mã>` ghép gia đình → nút "Đã gọi / Lừa đảo / An toàn" → handler `notify_guardian` gửi thật qua bộ đếm hạn mức `messages_out` | T + C | giao tin p95 ≤ 5 s; `docs/spikes/P1-S3-zalo.md`; ADR-010; chốt kênh dự phòng (trang `/a/[token]`) |
| 8 | **P1-S4 chọn model**: `HOICON_LLM_FAST_MODEL=claude-haiku-4-5 … spike bench --n 20` và `claude-haiku-5-5` | T/C | cập nhật ADR-009 §10, bảng §3 của spike S4 |
| 9 | **P1-S5 giọng nói**: `SpeechRecognizer` vi-VN trên máy + 20 câu tự thu; TTS (giọng đọc có sẵn của máy hay âm thanh thu sẵn) | T/C | `docs/spikes/P1-S5-giong-noi.md`; chốt "nút bấm là chính, giọng nói tùy chọn" |
| 10 | Ảnh `:demobank` + màn dừng ở cỡ chữ 100%/200% → `ux-elder-reviewer`; kiểm full-screen intent trên AVD 34/36 | T/C | hoàn tất §6 của spike S2 |
| 11 | **P1-01 cập nhật thuyết minh** qua `docs/proposal/src` (skill `pitch-sync`): đội ngũ thật, kết quả spike **có số đo**, Thông tư 77 (ghi rõ nguồn), thí điểm qua Play testing | M + C | Word + PDF mới; `pitch-sync` sạch |
| 12 | **P1-03 video 3 phút** (quay 05–08/11): cuộc gọi lạ → `:demobank` → màn dừng có giọng nói → tin Zalo cho con | M + T | file video; quay bằng `:demobank` với `secure=false`, không quay app ngân hàng thật |
| 13 | **P1-06 văn bản đồng ý v1 + DPIA rút gọn** (cần trước khi có người thật dùng) | C + M duyệt | `docs/legal/consent/`, `PRIVACY-DPIA.md` |
| 14 | Gate G1 (skill `phase-gate`) 08/11 → `judge` chấm thử 10/11 → sửa → **nộp 13/11** (P1-04) | M | biên nhận nộp |

**Nếu trễ** (danh sách cắt trong ROADMAP): bỏ P1-S6 → thu nhỏ P1-S5 → chỉ so 1 nhà cung cấp STT.
**Không bao giờ cắt**: sổ đồng ý, công khai AI, che PII, dừng an toàn, đường cảnh báo, trace, eval ≥ 100 ca.

### 5.3 Sau Vòng 1 (14/11 → 09/01) — xem bảng Phase 2 trong ROADMAP

Thứ tự gợi ý:
- P1-05…P1-09 (design system, Play internal, VPS);
- **P2-01/P2-03**: DB v1 + `IncidentService` + nối đồ thị P1-S4 vào `POST /v1/events`;
- **P2-02**: ghép đôi + đồng ý (E1–E4);
- **P2-05/06**: Lính gác v1 (Room + Tink, E6/E7);
- **P2-07**: cảnh báo Zalo + trang `/a/[token]` ⇒ gate M1 06/12;
- P2-08…P2-14: tác tử đầy đủ, diễn tập, bộ thí điểm ⇒ M2 20/12;
- P2-15…P2-21: eval ≥ 100 ca, hồ sơ vụ việc, Coach, web trace ⇒ nộp 09/01.

## 6. Tài khoản và quyền

| Tài khoản | Chủ | Cách chia cho người làm tiếp |
|---|---|---|
| GitHub repo | Minh | Tiến là **collaborator** (mời 14/10/2026): push, tạo nhánh, duyệt + merge PR, issue. Repo thuộc tài khoản cá nhân nên GitHub không có vai trò admin cho người khác; cần quyền quản trị (Settings, Secrets, quy tắc nhánh) thì chuyển repo sang một **Organization** rồi cấp vai trò Admin. Repo public: không commit bí mật, không đưa dữ liệu thật |
| Google Play Console | Minh (cá nhân) | Users and permissions → mời email của Tiến với quyền phát hành bản thử nghiệm |
| Firebase / Google Cloud | Minh | Project settings → Users → thêm Tiến (Editor) để chạy Test Lab |
| Anthropic API | Minh | Tạo **khóa riêng cho Tiến** trong workspace, đặt trần chi tiêu. Không chia chung một khóa, không dán khóa vào chat/issue |
| Zalo Bot Platform | Minh | token bot dev đưa qua kênh riêng (không qua repo); mỗi người một bot dev nếu được |
| VPS + tên miền (P1-09) | chưa có | ghi lại trong `docs/setup/` khi tạo |

## 7. Bản đồ mã nguồn

```
apps/android/        Kotlin/Compose — :rules (luật JVM thuần + BankAppCatalog sinh tự động), :app (Lính gác),
                     :demobank (ngân hàng giả), :latency (bộ đo cho Firebase Test Lab)
backend/src/hoicon/  api/ (FastAPI, /healthz, /readyz, /mcp/threat ở dev) · agents/ (incident_graph, runtime, llm_router,
                     prompts/, texts, spike CLI) · jobs/ (hàng đợi Postgres, worker) · domain/ (pii, risk, events) ·
                     mcp_servers/ (threat) · db/ (models, migration 0001–0002)
apps/web/            Next.js khung (chưa có trang nghiệp vụ)
data/                bank_apps.vn.json (sửa xong chạy `python scripts/gen-bank-apps.py`), scenarios/*.yaml,
                     threat_seed.demo.json, fixtures/phones.json (số hư cấu)
docs/                ROADMAP, ARCHITECTURE, DATA-MODEL, AGENTS, EVAL, adr/, spikes/, schemas/ (hợp đồng), setup/,
                     proposal/ (thuyết minh), research/ (nghiên cứu, bảng hỏi)
scripts/             setup-android, avd-create, emu-start, emu-scenario.py, ftl-latency.sh, gen-bank-apps.py, gen-api-client
.claude/             hook, subagent, skill, settings của Claude Code (HARNESS.md)
```

## 8. Rủi ro và lưu ý đã biết

| Rủi ro | Hiện trạng / cách xử lý |
|---|---|
| App ngân hàng thật tự dừng trên máy ảo/ADB/root (Thông tư 77/2025, theo nguồn thứ cấp) | Chỉ demo bằng `:demobank`; thử app thật trên máy thật đã tắt chế độ nhà phát triển, cài HỏiCon qua Play (giao thức §5 spike S2) |
| App ngân hàng có thể cảnh báo khi có app giữ quyền "hiển thị trên ứng dụng khác" | Chưa có bằng chứng; thử theo giao thức S2. Phương án: quyền này thành tùy chọn, dùng thông báo nổi + giọng nói |
| Số máy ảo ≠ máy thật | Không tuyên bố số liệu hay tương thích hãng nào chưa đo; ghi rõ nguồn số đo |
| Android 15+ phải tắt tối ưu pin cho HỏiCon | Bắt buộc trong onboarding E3 (ADR-007) |
| `/mcp/threat` chưa có xác thực | Chỉ gắn khi `HOICON_ENV=dev`; cần token + giới hạn tần suất trước P2-11 |
| Hạn mức Zalo Bot (3 bot × 50 người × 3.000 tin/tháng) | Đếm qua `messages_out`; dự phòng bằng trang hành động web |
| Máy dev của Minh: 16 GB RAM, ổ C gần đầy | Gradle/máy ảo có thể sập; đặt `UV_CACHE_DIR` sang ổ khác; cân nhắc chạy máy ảo trên máy của Tiến |

## 9. Xử lý sự cố thường gặp

| Triệu chứng | Cách xử lý |
|---|---|
| psycopg treo/lỗi trên Windows | dùng `SelectorEventLoop` (đã cấu hình sẵn ở test/alembic/uvicorn) |
| Gradle "insufficient memory for the Java Runtime" | đóng ứng dụng nặng, `gradlew --stop`, chạy `--no-daemon --max-workers=2`; trên Windows kiểm tra ổ chứa pagefile còn trống |
| CI android đỏ ở bước "generated bank catalog is up to date" | đã sửa `data/bank_apps.vn.json` mà quên chạy `python scripts/gen-bank-apps.py` |
| Test integration bị bỏ qua | Postgres chưa chạy: `docker compose -f infra/compose.dev.yml up -d` |
| `gh` không có trên PATH (Windows cài bằng winget) | gọi thẳng `…/WinGet/Packages/GitHub.cli_*/bin/gh.exe` |

## 10. Ai quyết định gì

- **Minh quyết**: phạm vi, cắt việc khi trễ gate, nội dung thuyết minh, mọi chuyện tài khoản/chi phí, phát hành cho người
  thật, dữ liệu thí điểm.
- **Người làm tiếp tự quyết** trong một task: thiết kế kỹ thuật bám ADR; muốn đổi quyết định đã chốt thì viết ADR mới
  (`docs/adr/ADR-0xx-*.md`) và để người còn lại duyệt trong PR.
- Ý tưởng ngoài phạm vi: ghi vào mục **Ghi chú** cuối ROADMAP, không tự làm.
