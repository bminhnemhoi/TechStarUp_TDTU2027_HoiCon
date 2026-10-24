# Master Plan HỏiCon — Spec-Driven Development tới 100% phạm vi

> Lập 15/10/2026 (Tiến + Claude, Minh đồng ý làm song song bằng worktree). **Vai trò của từng tài liệu:**
> - `docs/ROADMAP.md` — **trạng thái** từng task + gate + danh sách cắt (nguồn sự thật "đang ở đâu").
> - File này — **bản đồ** tính năng ↔ spec ↔ task ↔ phụ thuộc ↔ bằng chứng, và **cách làm** (Spec Kit, worktree).
> - `.specify/memory/constitution.md` — 9 nguyên tắc không thương lượng (tóm tắt CLAUDE.md + ADR).
> - `specs/NNN-slug/` — đặc tả, kế hoạch, task, bằng chứng của từng tính năng (tạo theo đợt).
> - `docs/HANDOFF.md` — bàn giao, dựng môi trường, tài khoản.
>
> **Phân quyền (Tiến chốt 15/10):** Tiến là kỹ sư chủ trì, **quyết định toàn bộ kỹ thuật** trên nhánh dev và các
> worktree. Minh là **reviewer ở cổng PR tổng của đợt** (`tien-collab-dev` → `main`, khi đợt xong, `evidence.md` đủ, test
> xanh). Không dừng giữa chừng chờ Minh duyệt từng task — xem §2.6. Quy trình tích hợp: §5 luật 5, §6 bước 6.

## 1. Audit trạng thái (15/10/2026)

> **Mốc code:** `origin/main` = `2f3f9f1` (mới có P1-S1). P1-S2, P1-S4, P1-07, HANDOFF nằm ở **PR #9**
> (`handoff/2026-10-14` = `80b006d`, CI xanh, mergeable, **chưa ai duyệt**). Bảng dưới mô tả trạng thái **sau khi #9 merge**.
> ⇒ Merge #9 (rồi Dependabot #5) là điều kiện trước mọi nhánh/worktree mới (§5).

| Nhóm | ✅ Xong + có bằng chứng | ◐ Dở / ⚠️ chưa kiểm chứng | ☐ Chưa làm |
|---|---|---|---|
| Android | Chuỗi cảm biến (CallScreening → FGS → UsageStats → SafePause), 50 app tài chính sinh code, `:demobank` có luồng chuyển tiền giả, `:latency`, `:rules` 49–51 test, lint 0 lỗi | ⚠️ p95 ≤ 3 s **chỉ có số máy ảo**; FSI chưa kiểm; tiêu đề demobank chồng dòng; `tts_unavailable` trên AVD Linux; TalkBack/overlay/rung chưa thử máy thật | Room + Tink, outbox, E1–E6, E8–E12, FCM, heartbeat, ghép đôi, diễn tập, buildType demo/release + R8 |
| Backend / AI | LangGraph 2 interrupt + `AsyncPostgresSaver` (sync), timer T1/T2/T3 bằng job, `recover()` sau kill -9, `llm_router` (≤ 4 s, raise-only, fallback), MCP `threat` (dev), `agent_steps`, PII mask/HMAC, migration 0001–0002, ~86 test | ⚠️ chưa gọi LLM thật (chưa có khóa); model chưa chốt; MCP `threat` không xác thực | API `/v1/*`, `IncidentService`, DB v1, Zalo, verification/rescore/case_file, coach, SSE, retention, eval CLI |
| Web | Next.js khung + client TS sinh từ OpenAPI | — | `/a/[token]`, dashboard, `/trace`, `/eval`, `/sim`, `/booth` |
| Dữ liệu | `bank_apps.vn.json` v1, 60 kịch bản nháp (`draft: true`), fixture số hư cấu | ◐ kịch bản chờ Minh duyệt | ≥ 100 ca eval, injection suite |
| Hạ tầng / CI | 5 workflow xanh, gitleaks, 7 hook bảo vệ, môi trường emulator Linux (W0-1) | — | VPS, Caddy, `compose.prod.yml`, sao lưu, Crashlytics, Play internal |
| Hồ sơ | Thuyết minh v1 (~50 trang), bảng hỏi P1-02 | — | Google Form + 300 phản hồi, cập nhật thuyết minh, video 3', poster, slide |
| Tài khoản (P0-08) | `gh`, cloudflared | ⏸ Minh đang đăng ký | Firebase, Play Console (cần máy thật xác minh), Zalo Bot, Anthropic, Gemini |

### Điểm bất hợp lý (nêu để quyết — chưa sửa)
| # | Vấn đề | Bằng chứng | Đề xuất | Ai quyết |
|---|---|---|---|---|
| B1 | CLAUDE.md nhắc skill `state-transition`, `consent-copy`, lớp Android `PiiMasker` — chưa tồn tại | `ls .claude/skills`; grep `PiiMasker` = 0 | Tạo khi làm spec 011/021/022 | Minh |
| B2 | Danh sách cắt có "chuyển người giám hộ thứ hai" nhưng T2 đã code (P1-S4) | `docs/AGENTS.md` mục "Đã có" | Bỏ khỏi danh sách cắt | Minh |
| B3 | DoD đòi `run-eval smoke` khi đổi prompt nhưng chưa có CLI eval | không có module eval trong `backend/src` | Spec 030 (eval smoke) làm **trước** 024 | Minh |
| B4 | Thuyết minh cam kết 50–100 gia đình thí điểm; gate chỉ ≥ 20 (M3) / ≥ 30 (G3) | thuyết minh tr.4; ROADMAP gate | Hạ cam kết trong P1-01 (khuyên, trung thực) hoặc nâng gate | Minh |
| B5 | Thuyết minh có nhóm "sinh viên"; PRD chỉ người cao tuổi; P1-01 ghi "đội 1 người" | thuyết minh tr.4; PRD; ROADMAP P1-01 | Ghi đội 2 người; sinh viên = mở rộng sau MVP | Minh |
| B6 | Hồ sơ `judge` cần nhà cung cấp khác bên sinh — chưa có provider Gemini | `docs/AGENTS.md` | Eval chấm tất định là chính; LLM-judge Gemini khi có khóa | Minh |
| B7 | M2 cần ≥ 5 gia đình cài qua Play nhưng Play Console chưa đăng ký | HANDOFF §5.1 | Đăng ký ngay — đường găng M2 | Minh |
| B8 | Gate G1 đòi 5 báo cáo spike; S3, S5 chưa bắt đầu, S6 nhiều khả năng cắt | ROADMAP gate G1 | Cắt P1-S6 ngay ⇒ G1 = 4 spike + ADR-007…010 | Minh |

## 2. Spec Kit cho dự án brownfield

### 2.1 Nguyên tắc
1. **Tài liệu cũ vẫn là nguồn sự thật**: ROADMAP (trạng thái), ADR (quyết định), `docs/schemas/` (hợp đồng),
   DATA-MODEL (bảng). Spec chỉ **trỏ tới** và ghi **phần chênh lệch**.
2. **Không spec lại việc đã xong** (P0, S1, phần đã đo của S2, lõi S4) — chúng là baseline ở §1.
3. **Hai làn quy trình:**
   - **Full** (tính năng mới, đổi hành vi, hợp đồng, DB, quyền, UI, prompt):
     `specify → clarify → plan → tasks → analyze → checklist → implement → converge → evidence → review → PR`.
   - **Lite** (≤ 1 ngày, không đổi hành vi hay hợp đồng: đo đạc, tài liệu, bump phụ thuộc, sửa lỗi nhỏ có test):
     task ROADMAP + PR, không cần thư mục spec.
4. **Số spec cấp trước** ở §3 — hai worktree không tranh số. Tạo spec luôn truyền thư mục đã cấp
   (`SPECIFY_FEATURE_DIRECTORY=specs/NNN-slug`).

### 2.2 Đã cài (Spec Kit CLI 1.1.3, tích hợp `claude`, script `sh`)
- `.specify/` (scripts, templates, workflow, `memory/constitution.md`) + `.claude/skills/speckit-*` (lệnh `/speckit-<bước>`).
- **Không** cài extension `git` (đã có quy ước nhánh) và `agent-context` (CLAUDE.md do người viết). `specify init` có
  định dạng lại `.claude/settings.json` (nội dung không đổi) — đã khôi phục bản gốc; nếu chạy lại `init` thì làm tương tự.
- `.specify/feature.json` bị bỏ qua khỏi git (CLI quản lý) ⇒ mỗi worktree tự nhớ spec đang làm.
- `/speckit-taskstoissues` có sẵn nhưng **không dùng** (đã deprecated; issue không phải nguồn sự thật).

### 2.3 Tùy biến cho HỏiCon (`.specify/templates/overrides/`, CLI ưu tiên cao nhất)
- `spec-template.md`: thêm **Truy vết** (mã ROADMAP, US-xx, ADR, gate, phụ thuộc, làn), **Bất biến an toàn**,
  **Quyền riêng tư & đồng ý**, **UX người cao tuổi**, SC ghi **môi trường đo**, **Kế hoạch bằng chứng**, **Ngoài phạm vi & mốc cắt**.
- `plan-template.md`: Technical Context điền sẵn stack; **Constitution Check** 9 dòng; mục **Tái sử dụng** bắt buộc;
  cây thư mục monorepo thật; mục Thiết kế & trade-off.
- `tasks-template.md`: test **bắt buộc**; mỗi task ghi `FR-xxx` + `Verify: \`lệnh\``; phase cuối **Acceptance evidence**.
- `evidence-template.md`: SC ↔ số đo + nguồn, FR ↔ test, cổng các tầng, review, converge, còn tồn.
- `.specify/memory/checklists.md`: nội dung cho `/speckit-checklist privacy | elder-ux | release-block`.

### 2.4 Vòng tự kiểm của coding agent (chống "xong trên giấy")
1. `/speckit-analyze` sau `tasks` ⇒ **0 CRITICAL/HIGH** mới được implement.
2. `/speckit-implement` từng phase; mỗi task chạy `Verify:`; đỏ thì dừng phase đó.
3. `/speckit-converge` sau implement (so code với spec/plan/tasks, chỉ ghi thêm task còn thiếu), tới khi **0 finding** hoặc chạm điều kiện dừng §2.5.
4. Cổng các tầng bị đụng tới: backend `ruff` + `pytest` · `:rules:test :app:lintDebug` · web `typecheck lint test` ·
   hook test · `emu-scenario.py` (cảm biến) · `run-eval smoke` (prompt/đồ thị/model).
5. `evidence.md` → reviewer: `security-privacy-reviewer`, `ux-elder-reviewer`, `/ponytail-review`.
6. `python3 scripts/check-spec-trace.py` (CI job `harness/spec-trace` chạy trên mọi PR đụng `specs/`, `.specify/`,
   ROADMAP, Master Plan): thư mục spec có trong danh mục §3; link ROADMAP có thật; mọi FR có task; tasks tick hết ⇒
   có `evidence.md` thật (mỗi SC-xxx có dòng số đo điền đủ); ROADMAP ☑ ⇒ spec xong thật.

### 2.5 Điều kiện dừng (tránh lặp vô hạn, tránh phình phạm vi)
| Vòng | Dừng khi | Nếu chưa đạt |
|---|---|---|
| `analyze` (chỉ đọc, ≤ 50 finding) | 0 CRITICAL/HIGH | sửa spec/plan/tasks tối đa **2 vòng**; còn CRITICAL/HIGH ⇒ dừng, hỏi người. MEDIUM/LOW ghi vào plan, không chặn |
| `implement` từng task | `Verify:` xanh | đỏ **2 lần liên tiếp** ⇒ dừng task, chẩn đoán (skill `diagnosing-bugs`); **không** sửa test cho xanh |
| `converge` (chỉ ghi thêm, giới hạn trong phạm vi artifact) | 0 finding | tối đa **3 vòng**; vòng sau không giảm số finding ⇒ dừng, báo người |
| Finding bị chặn bởi bên ngoài (tài khoản, máy thật, quyết định phạm vi/hồ sơ ★ chưa chốt) | — | **không** thêm task code: ghi `BLOCKED: <lý do>` trong `evidence.md` + ghi chú ở dòng task ROADMAP; spec chưa được ☑ |
| Finding ngoài phạm vi spec | — | không làm; ghi vào "Ghi chú" ROADMAP (qua PR từ checkout chính) |
| Checklist (`/speckit-implement` dừng hỏi khi còn mục chưa tick) | người review (Tiến/Minh hoặc reviewer agent) đã tick | không tự tick để qua cổng |

### 2.6 Tự hành một mạch (run-to-completion) — áp dụng mọi spec từ 004 trở đi
- `tasks.md` **không** có task kiểu "dừng chờ Minh duyệt" giữa chừng. Quyết định kỹ thuật (thiết kế bảng, mã hóa,
  thư viện, nội dung ADR) chốt trong `plan.md`/`research.md` lúc lập kế hoạch, Tiến duyệt **trước** `implement`; sau đó
  agent chạy từ task đầu tới phase **Acceptance evidence** không ngắt.
- ADR mới viết **đầy đủ** ngay trong spec (trạng thái "Đã chấp nhận — Tiến, <ngày>"); Minh xem cùng PR tổng của đợt.
- Thứ chỉ có từ bên ngoài (token, tài khoản, máy thật) **không** là điểm dừng: dùng mock/đường thay thế, task đó ghi
  `BLOCKED: <lý do>` trong `evidence.md` (§2.5) rồi làm tiếp các task còn lại.
- Điểm dừng hợp lệ duy nhất: điều kiện dừng §2.5 (analyze còn CRITICAL/HIGH sau 2 vòng, `Verify:` đỏ 2 lần, converge
  không giảm) và nguy cơ vi phạm hiến chương/CLAUDE.md (dừng, báo Tiến).
- Cổng người duy nhất của Minh: review + merge PR tổng của đợt (`tien-collab-dev` → `main`).

## 3. Danh mục tính năng (100% phạm vi, số spec cấp trước)

Làn: **A** = Android · **B** = backend/AI/web · **H** = hồ sơ, vận hành (không dùng Spec Kit; dùng `pitch-sync`, `judge`,
`phase-gate`). Spec tạo **theo đợt**, 1–2 tuần trước khi làm. AC = tiêu chí nghiệm thu chính (spec chi tiết hóa thêm).

### Đợt 0 — Gỡ chặn + dựng Spec Kit (15–19/10)
| ID | Nội dung | Làn | AC chính | Bằng chứng |
|---|---|---|---|---|
| W0-1 (lite) | Môi trường emulator Linux + tài liệu đường dẫn cho cả Windows và Linux | A | CI xanh; `emu-start.sh hc-api36 --headless` chạy trên Linux; Windows không đổi hành vi | log CI |
| W0-2 (lite) | Spec Kit: constitution, override, `check-spec-trace.py` + CI, file này, `specs/README.md` | B | `specify check` OK; test cũ xanh; `check-spec-trace` xanh | diff, output |
| W0-3 (H) | P0-08 tài khoản: **Play Console + Firebase tuần này**, Zalo, Anthropic (trần 10–20 USD) | Minh | `check_keys` Đạt | — |
| W0-4 (H) | Google Form P1-02 + phát tán | Minh + Tiến | ≥ 100 phản hồi 28/10 · ≥ 300 trước 08/11 | báo cáo số liệu |

### Đợt 1 — Spike còn lại + hồ sơ Vòng 1 (20/10–13/11)
| Spec | Nội dung (ROADMAP) | Làn | Phụ thuộc | AC chính | Bằng chứng |
|---|---|---|---|---|---|
| **001-safe-pause-real-device** | P1-S1/S2 còn lại: `:latency` trên FTL ≥ 2 máy (Samsung A + Pixel), kiểm FSI khi từ chối SAW (AVD 34/36), sửa tiêu đề demobank chồng dòng, sửa `tts_unavailable` trên AVD, ảnh → `ux-elder-reviewer`, đóng phần mở của ADR-007/008 | A | Firebase | p95 `app_foreground→pause_shown` ≤ 3 s **máy thật**, hoặc ghi rõ không đạt + phương án (View thuần, R8/baseline profile) | `device-matrix.md`, ảnh 100/200%, báo cáo reviewer |
| **002-zalo-guardian-channel** | P1-S3: webhook `POST /webhooks/zalo/{bot_id}` (kiểm secret, chống trùng, trả 200 ngay, xử lý bằng job), `/start <mã>`, nút Đã gọi/Lừa đảo/An toàn, `notify_guardian` gửi thật qua `messages_out`, chế độ **mock** cho test/CI, ADR-010 | B | token Zalo; dùng lại `jobs/queue.py`, `agents/texts.py` | giao tin p95 ≤ 5 s (n ≥ 20); tin mở đầu "Đây là trợ lý AI HỏiCon"; hết hạn mức ⇒ rơi về `/a/[token]` | `docs/spikes/P1-S3-zalo.md` |
| **003-agent-core-mcp-threat** | P1-S4 còn lại (Tiến nâng từ lite thành spec đầy đủ 15/10): `threat_indicators` chỉ HMAC + lệnh nạp, MCP `threat` có token + giới hạn tần suất (kéo sớm từ 026), `spike bench --model --json`, trần chi tiêu bền | B | 002, 030; khóa Anthropic chỉ chặn phần so model | MCP không token ⇒ 401, vượt hạn mức ⇒ 429; 0 h1 trên đĩa máy chủ; eval smoke +0 | `evidence.md`; số model BLOCKED tới P0-08 |
| **004-voice-vi** | P1-S5 thu nhỏ: TTS trên máy (giọng có sẵn vs âm thanh thu sẵn); STT `SpeechRecognizer` vi-VN 20 câu tự thu; chốt "nút bấm là chính" | A | — | quyết định có số; TTS chạy offline trên AVD + máy thật | `P1-S5-giong-noi.md` |
| 005 (lite) | P1-07: Minh duyệt 60 kịch bản ⇒ `draft: false` | Minh | — | `test_scenarios.py` xanh | — |
| H-1 | P1-01 thuyết minh (xử lý B4, B5; số đo spike có nguồn; đội 2 người) · P1-03 video 3' (`:demobank`, máy ảo) · P1-04 `judge` 10/11 → nộp 13/11 | H | 001, 002 cho cảnh demo | `pitch-sync` sạch; video ≤ 3' | biên nhận nộp |
| — | P1-S6 (R2 sideload) | — | — | **đề xuất ✂ ngay** (B8) | — |

**Gate G1 (08/11):** 4 báo cáo spike + ADR-007…010 + video.

### Đợt 2 — Chuẩn bị MVP (14–22/11)
| Spec | Nội dung | Làn | Phụ thuộc | AC chính |
|---|---|---|---|---|
| **010-design-system** | P1-05: `docs/DESIGN-SYSTEM.md` + `design-system/hoicon/tokens.json` (Be Vietnam Pro), sinh cả theme Compose + CSS vars | A+B | — | tương phản ≥ 7:1 có test; token dùng chung hai nền tảng |
| **011-consent-legal** | P1-06: văn bản đồng ý v1 theo từng mục đích (enum + phiên bản + sha256), DPIA rút gọn, PILOT-PROTOCOL; skill `consent-copy` (B1) | B + Minh duyệt | — | mỗi mục đích có 1 văn bản; test enum ↔ văn bản khớp |
| **012-release-and-hosting** | P1-08 + P1-09 + P2-04: buildType `demo`/`release` (R8, tắt log chẩn đoán, baseline profile), Play internal + Google Group; VPS + Caddy + `compose.prod.yml` + backup Postgres hằng ngày | A+B | Play Console | AAB lên internal testing; `https://…/healthz` 200; khôi phục backup thử thành công; đo lại khởi động nguội (hạn sàng lọc 5 s của Telecom) |

### Đợt 3 — Lát dọc MVP tới M1 (23/11–06/12)
| Spec | Nội dung | Làn | Phụ thuộc | AC chính |
|---|---|---|---|---|
| **020-family-pairing-consent** | P2-01 + P2-02: DB v1 (families, members, devices, consents chỉ ghi thêm có trigger, trusted_contacts, pairing_codes, action_tokens), `/v1/pair`, JWT thiết bị + refresh, `/v1/consents`, màn E1–E4 (E3 công bố nổi bật + "Không giới hạn pin") | A+B | 010, 011 | US-01 ghép đôi < 5'; mã 6 số hết hạn 15'; mỗi quyền đã cấp có dòng consent; UPDATE/DELETE `consents` bị chặn (test) |
| **021-events-incident-service** | P2-03: `POST /v1/events` theo lô idempotent (UUIDv7, `risk_event.v1.json`); `IncidentService.transition()` + `incident_transitions` + khóa lạc quan; nối đồ thị P1-S4; skill `state-transition` (B1) | B | 020 | gửi trùng lô không nhân bản; mọi chuyển trạng thái qua service (test); sự cố mở ≤ 1 s sau event |
| **022-sentinel-v1** | P2-05 + P2-06: Room + Tink thay SharedPreferences, outbox gửi lại an toàn, heartbeat, E6 "Đang bảo vệ", E7 chốt (View/Compose theo số của 001), nút "Hỏi con" thật, `PiiMasker` (B1); **I1** luật R5 + **I2** câu nhắc mật khẩu gia đình (nếu duyệt) | A | 001, 020 | US-02: SafePause p95 ≤ 3 s offline; tắt backend vẫn hiện SafePause; outbox gửi lại sau mất mạng (test); không còn SharedPreferences cho dữ liệu rủi ro |
| **023-guardian-alert** | P2-07: cảnh báo giai đoạn 1 (tin mẫu, không LLM) qua Zalo + trang `/a/[token]` (action token 1 lần) + `POST /v1/incidents/{id}/decision` | B | 002, 021 | US-03: Zalo p95 ≤ 10 s; 4 nút; quyết định người giám hộ đóng được sự cố; token dùng 1 lần, có hạn |
| **E2E-M1** (nằm trong 023) | `scripts/e2e-m1.sh`: emulator (cuộc gọi lạ → demobank) + backend + Zalo mock ⇒ JSON bằng chứng | A+B | 020–023 | Gate M1: AVD 34 + 36 đạt; 0 số điện thoại thô trong DB/log (`privacy-audit`) |

### Đợt 4 — Tác tử đầy đủ + thí điểm tới M2 (07–20/12)
| Spec | Nội dung | Làn | Phụ thuộc | AC chính |
|---|---|---|---|---|
| **030-eval-smoke** (kéo lên sớm — O1) | CLI `hoicon-eval` + 20 ca smoke chạy bằng phản hồi LLM ghi sẵn (tất định, chạy được trong CI) | B | 005 | < 1 phút; đo recall leo thang, báo nhầm, vi phạm an toàn, công khai AI |
| **024-risk-and-intervention** | P2-08 + P2-09: `risk_scorer` + ngân hàng câu hỏi, E8 qua FCM, `intervention`, T1/T2/T3 nối Zalo thật | A+B | 021, 023, 030 | US-05 tóm tắt ≤ 15 s; LLM quá hạn ⇒ mẫu; eval smoke không tụt so với baseline |
| **025-trace-sse** | P2-10: `agent_steps` + SSE `/v1/runs/{id}/stream` | B | 021 | trace đủ node, đã che PII |
| **026-verification-threat** | P2-11: tác tử xác minh + `rescore`, `/v1/lookups`, E10, đồng bộ danh sách đe dọa xuống máy (MCP token + hạn mức + `threat_indicators` đã làm ở 003) | A+B | 024, 003 | US-06 có nguồn dẫn |
| **027-guardian-web** | P2-12: danh sách/chi tiết sự cố cho người giám hộ | B | 023 | Playwright + ảnh chụp |
| **028-drills** | P2-13: diễn tập v1 (E11, bảng `drills`, nhãn `[DIỄN TẬP]`, màu riêng, debrief) | A+B | 022, 024 | US-08; `is_drill` ở mọi nơi (test) |
| **034-hardening-core** | Phần P2-20 cần **trước** người thật: `privacy-audit`, review bảo mật, job retention, backup | B | 012 | 0 lỗi bảo mật High |
| **029-pilot-kit** | P2-14: bộ thí điểm + Play internal v0.3 | A+B+H | 012, 020, 022, 034 | Gate M2: ≥ 5 gia đình, ≥ 1 máy thật, heartbeat ≥ 90%, crash-free ≥ 99% |

### Đợt 5 — Hoàn thiện Vòng 2 (21/12–09/01, đóng băng 06/01)
| Spec | Nội dung | Làn | Phụ thuộc | AC chính |
|---|---|---|---|---|
| **036-eval-full** | P2-15 + P2-18: ≥ 100 ca (≥ 30% hợp lệ, ≥ 10 injection), baseline, lặp prompt | B | 030, 024 | Gate M3: recall ≥ 0,90; leo thang nhầm ≤ 0,10; 0 vi phạm an toàn; công khai AI 100% |
| **031-case-file** | P2-16: nhánh `case_file` + interrupt duyệt | B | 024 | US-07 |
| **032-coach-weekly** | P2-17: Coach hằng tuần + **I4** (tin "Tuần này nhà mình an toàn", báo "mất bảo vệ" từ heartbeat) | B | 022, 023 | trong hạn mức Zalo (đếm `messages_out`) |
| **033-web-sim-eval** | P2-19: `/trace` (xyflow), `/eval`, `/sim` | B | 025, 036 | US-10 |
| **037-hardening-rest** | P2-20 còn lại: Crashlytics, rà soát cuối | A+B | 034 | crash-free đo được |
| H-2 | P2-21: báo cáo thí điểm, poster, video 5', nộp 09/01 | H | — | `pitch-sync` sạch |

### Đợt 6 — Thí điểm + chung kết (14/12–27/02)
| Spec | Nội dung | Làn | AC chính |
|---|---|---|---|
| H-3 | P3-01…04: vận hành thí điểm, diễn tập theo PILOT-PROTOCOL, chiến dịch Tết, báo cáo số liệu v2 | H | Gate G3 |
| **050-booth-mode** | P4-02: `/booth`, `/join/[code]`, `/demo/console`, phát lại khi mất mạng, reset demo < 1' | A+B | Gate G4: chạy 3 lần liên tiếp, cảnh báo < 5 s |
| H-4 | P4-01/03/04: sửa theo BGK, slide 10', tổng duyệt 3 lần với `judge` | H | — |

**Danh sách cắt:** giữ thứ tự ROADMAP (trừ B2 nếu được duyệt). **Không bao giờ cắt:** sổ đồng ý, công khai AI, che PII,
dừng an toàn, đường cảnh báo, trace, eval ≥ 100 ca.

### Đường găng
`Play Console + Firebase (W0-3)` → `001` → `012` → `022` → `029 (M2)` · `Zalo (W0-3)` → `002` → `023 (M1)` →
`024` → `036 (M3)`. Trễ ở đầu chuỗi đẩy lùi gate ⇒ ưu tiên gỡ tài khoản trước mọi việc code.

## 4. Ý tưởng + tối ưu (đánh giá khách quan)
| ID | Nội dung | Đề xuất | Chi phí | Vào spec |
|---|---|---|---|---|
| I1 | Luật R5: app điều khiển từ xa (AnyDesk, UltraViewer, TeamViewer…) lên tiền cảnh trong cửa sổ cuộc gọi lạ ⇒ `critical` (khai `<queries>` theo tên gói, không `QUERY_ALL_PACKAGES`) | **Làm** — cần Minh duyệt + bổ sung ADR-001 | ~1 ngày | 022 |
| I2 | Câu nhắc "Hỏi người gọi mật khẩu gia đình" ở E7/E9 (không lưu mật khẩu) | **Làm** | vài giờ | 022/023 |
| I3 | Nhận biết cuộc gọi Zalo/Messenger (`MODE_IN_COMMUNICATION`) ⇒ nhắc nhẹ | Spike sau khi có máy thật, sau cờ tắt mặc định; thuyết minh ghi là hướng phát triển | 1–2 ngày | sau M1, cắt được |
| I4 | Tin Zalo hằng tuần + báo "mất bảo vệ" | **Gộp** vào 032 | thấp | 032 |
| I5 | Giọng con thu sẵn trong SafePause | Chỉ đưa vào thuyết minh (lộ trình 2027) — con không cài app, cần quyền micro/đồng bộ | — | H-1 |
| O1 | Eval smoke trước tác tử | **Làm** (B3) | — | 030 trước 024 |
| O2 | Chốt E7 View thuần hay Compose bằng số máy thật (View nhanh hơn ~0,8 s khi nguội trên máy ảo) | **Làm** | — | 001 → 022 |
| O3 | R8 + baseline profile cho khởi động nguội kịp hạn sàng lọc 5 s | **Làm** | thấp | 012 |
| O4 | Zalo mock + `e2e-m1.sh` dùng chung cho test, gate, gian trưng bày | **Làm** | thấp | 002, 023 |
| O5 | `/a/[token]` là kênh dự phòng chính khi Zalo hết hạn mức | **Làm** | có trong 023 | 023 |

## 5. Làm song song bằng git worktree (trần 2 worktree — CLAUDE.md)

**Bố cục trên máy Tiến:**
```
~/Projects/TechStarUp_TDTU2027_HoiCon   # checkout chính: docs, ROADMAP, schemas, review, merge
~/Projects/hoicon-wt/android            # làn A: apps/android/**, data/bank_apps*, scripts/emu-*, scripts/ftl-*
~/Projects/hoicon-wt/server             # làn B: backend/**, apps/web/**, infra/**
```

**Tạo / dùng / dọn:**
```bash
# Nhánh spec tách từ nhánh tích hợp tien-collab-dev (luật 5), không từ main.
git fetch origin
git worktree add -b feat/001-safe-pause-real-device ../hoicon-wt/android origin/tien-collab-dev
git worktree add -b feat/002-zalo-guardian-channel ../hoicon-wt/server origin/tien-collab-dev
# worktree đã có: git -C ../hoicon-wt/<làn> switch -c feat/NNN-slug origin/tien-collab-dev
# trong từng worktree:
uv sync --directory backend          # .venv riêng mỗi worktree
pnpm install                         # store pnpm dùng chung ⇒ nhanh
# Tiến tự chép backend/.env và .claude/settings.local.json sang (Claude không đọc .env)
git worktree list
# sau khi PR tổng của đợt merge vào main:
git worktree remove ../hoicon-wt/android && git branch -d feat/001-safe-pause-real-device
```

**Luật để không giẫm chân nhau:**
1. **Sở hữu theo đường dẫn:** làn A không sửa `backend/**`; làn B không sửa `apps/android/**`. File chung
   (`docs/schemas/**`, `docs/ROADMAP.md`, `docs/MASTER-PLAN.md`, `CLAUDE.md`, `.specify/memory/**`) sửa ở checkout chính
   trên `tien-collab-dev` và **đẩy trước** (hợp đồng trước); hai làn `git rebase origin/tien-collab-dev` sau đó.
2. **Chỉ làn B tạo migration Alembic** (tránh hai head). Làn A cần API thì dùng DB riêng `hoicon_android`
   (`HOICON_DATABASE_URL` trong `.env` của worktree đó) + cổng API 18001 / web 3101. Container Postgres 15432 dùng chung.
3. **Chỉ làn A dùng máy ảo** (một emulator, 14 GB RAM). Không chạy Gradle ở hai làn cùng lúc. Trước buổi chạy máy ảo,
   hỏi Tiến trước khi dừng stack Docker khác.
4. **Mỗi worktree một phiên Claude Code** (một pane Orca), mỗi phiên đúng một spec. `.specify/feature.json` riêng từng
   checkout nên `/speckit-*` không lẫn spec.
5. **Tích hợp trực tiếp vào `tien-collab-dev`** (Tiến chốt 15/10): không mở PR từng spec. Spec xong (§6 bước 5) ⇒ ở
   checkout chính chạy cổng (`check-spec-trace.py`, `unittest scripts/tests`, `pytest`, Gradle khi đụng Android), quét
   gitleaks các commit mới, rồi `git merge --no-ff feat/NNN-slug` và `git push origin tien-collab-dev`. Luôn giữ **một
   Draft PR tổng** `tien-collab-dev` → `main` (hiện là **#12**) để CI chạy trên mỗi lần push (workflow chỉ chạy trên PR +
   push `main`). Cuối đợt bỏ Draft ⇒ Minh nghiệm thu một lần. Rebase nhánh spec lên `origin/tien-collab-dev` hằng ngày;
   không push thẳng `main`.
6. Minh (Windows, ít RAM) không cần worktree: nhận làn H + review PR tổng của mỗi đợt (cổng merge `main`).
7. **Spec hai làn (A+B: 010, 012, 020, 024, 026, 028, 029, 037, 050):** `spec.md` + `plan.md` + `tasks.md` + schema viết
   **một lần** ở checkout chính và đẩy lên `tien-collab-dev` trước; sau đó mỗi làn mở nhánh riêng, chỉ làm và tick task
   thuộc đường dẫn của mình. `converge` + `evidence.md` do người tích hợp sau cùng chạy một lần trên `tien-collab-dev`.
8. **ROADMAP trong nhánh tính năng:** chỉ sửa **dòng task của mình**. Khối STATUS và "Ghi chú" chỉ sửa ở checkout chính
   sau khi merge (khối STATUS là điểm xung đột thường gặp nhất).
9. **Sau khi PR tổng squash-merge vào `main`:** `tien-collab-dev` không còn là tổ tiên của `main` ⇒ đặt lại
   `tien-collab-dev` từ `origin/main` mới (Tiến làm, `git push --force-with-lease`) và `git rebase --onto` các nhánh spec
   còn mở; với thay đổi chưa commit: `git stash -u` trước, `git stash pop` sau.
10. **File sinh tự động có chủ:** `BankAppCatalog.kt` (`:rules`) + khối `<queries>` trong `AndroidManifest.xml` sinh từ
    `data/bank_apps.vn.json` (làn A, `python scripts/gen-bank-apps.py`; I1 cũng đi đường này); `apps/web/src/lib/api/schema.d.ts` sinh từ OpenAPI backend (làn B,
    `bash scripts/gen-api-client.sh`). Không sửa tay, không sinh ở làn không sở hữu.

**Ghép cặp theo đợt:** Đợt 1: A = 001 → 004 · B = 002 (+ 003 lite). **Đang chạy (Tiến giao 15/10/2026, gọi là "Đợt 3" của lịch tích hợp):** A = 010 · B = 003 (đầy đủ). Đợt 2: A = 012 (phần Android) · B = 011 → 012 (VPS).
Đợt 3: B = 020 (API) → 021 → 023 · A = 020 (màn E1–E4, sau khi hợp đồng merge) → 022. Đợt 4: B = 030 → 024 → 025/026/027 ·
A = 024 (E8) → 028.

**Wave 3 (xếp 22/10/2026, sau khi gộp Wave 2 `afe8707`).** Nguyên tắc: an toàn trước (F-2), rồi thứ phục vụ video Vòng 1
(`/sim` + `/trace`), rồi 031 → 032 (cùng văn bản `guardian_alerts`), `/eval` (P3, cắt được) cuối. Mỗi mục trỏ đúng task;
Verify và điều kiện dừng nằm trong `tasks.md` của spec.

| # | Làn A (Android, `hc-api36`/`hc-api34`) | Làn B (backend + web) |
|---|---|---|
| 0 | **Đối soát Wave 2** (mã đã gộp ở `afe8707` nhưng `tasks.md` chưa tick): chạy Verify rồi tick + evidence cho 026 T032, 011 T018, 028 T023, 012 T016, 012 T018 | **Đối soát Wave 2** (`a171bc2`): chạy Verify rồi tick + evidence cho 011 T019, 012 T017, 012 T019 |
| 1 | 010 **T028** (chuỗi E7 điều khiển từ xa đã chốt, chụp lại 4 ảnh, reviewer 0 High; đóng luôn T027) | **F-2 an toàn:** 024 **T014** → **T015** → 036 **T025** → **T026** → **T027** → **T028** → 024 **T018** → **T019** |
| 2 | *(nếu Tiến duyệt nới quyền, dưới đây)* 033 **T012** (`trace-graph.tsx`, dựng từ fixture `graph_topology` trong `docs/schemas/fixtures/`, chưa cần API) | 033 [B-api] **T002** → **T003** → **T004** → **T005** → **T006** → **T007** → **T008** → **T009** → **T011** (sinh client TS: mở khóa web) |
| 3 | *(nới quyền)* 033 **T013** `/trace` → **T014** `/sim` → **T015** (sau làn B T011) | *(không nới quyền: làn B tự làm 033 T012 → T013 → T014 → T015 ở đây, rồi mới sang 031)* |
| 4 | 031 **T014** (đồng bộ chuỗi `guardian_alerts` Android **một lần** cho cả 031 và 032 — xem dưới; sau làn B 031 T011) | 031 [B-api] **T002** → **T003** (migration) → **T004** → **T005** → **T006** → **T007** → **T008** → **T009** → **T010** → **T011** (văn bản gộp) → **T012**; [B-web] **T013** (hoặc làn A nếu nới quyền) |
| 5 | 032 **T011** (đo khoảng trống heartbeat; cần backend dev có 032 T004); 032 **T010** gộp vào 031 T014 — chỉ chạy lại khi 032 T008 đổi chữ (Minh bác I4) | 032 **T001** (migration) → **T002** → … → **T007** → **T008** (chỉ kiểm, chữ đã vào ở 031 T011) → **T009** |
| 6 | *(nới quyền)* 033 **T016** `/eval` (P3) | 033 **T010** (P3, `GET /v1/eval/summary` + `.dockerignore`) → rà soát/nghiệm thu: 033 **T017–T019**, 031 **T015–T016**, 032 **T012–T013** |
| — | Chen khi Minh quyết F-1 = A: không có việc Android (E8 không đổi) | 024 **T016** → **T017** chen trước 024 T018 |

**Văn bản `guardian_alerts` (031 ↔ 032, chốt 22/10):** một lần sửa duy nhất ở 031 T011, gồm cả câu của 032 (bản tin tuần + báo
"mất bảo vệ") để không vượt trần 160 từ hai lần và Android chỉ đồng bộ một lần. Chữ chốt (160/160 từ, qua `style_problems`) nằm ở
`specs/031-case-file/tasks.md` T011. Văn bản vẫn `draft`, chưa `released` cho tới khi 032 merge (lời hứa "báo khi máy hết được
bảo vệ" phải có mã thật trước khi phát hành — luật của 011 T019). Minh bác I4 ⇒ 032 T008 bỏ cụm "báo khi máy bác hết được bảo
vệ," (văn bản còn 153 từ), tăng phiên bản, 032 T010 đồng bộ lại.

**Đề xuất nới quyền làn A cho [B-web] của 033 — CHỜ TIẾN DUYỆT (chưa áp dụng; luật 1 §5 vẫn giữ nguyên tới khi Tiến ghi "đồng ý").**
- *Lý do:* sau 010 T028, làn A chỉ còn việc chờ làn B (031 T014 cần 031 T011; 032 T011 cần 032 T004) ⇒ ~3–5 ngày rảnh, trong khi
  làn B phải làm nối tiếp F-2 → 033 API → 033 web → 031 → 032. Cho làn A làm 033 [B-web] rút đường găng làn B khoảng 2–3 ngày và
  `/sim` + `/trace` (cần cho video) xong sớm hơn.
- *Ranh giới:* làn A được sửa **chỉ** `apps/web/**` (trừ `apps/web/src/lib/api/schema.d.ts` — tệp sinh của làn B, luật 10) và chỉ
  các task 033 T012–T016 (+ 031 T013 nếu còn rảnh). **Không** `backend/**`, **không** migration, **không** `infra/**`, không sinh
  client TS (dùng bản làn B đã đẩy lên `tien-collab-dev`). Web dev chạy cổng **3101** với API **18001** của làn A (luật 2) — hoặc
  trỏ API 18000 của làn B khi làn B đang chạy. Một spec một phiên: làn A làm 033-web trên nhánh riêng `feat/033-web-sim-eval-web`.
- *Rủi ro và chặn:* (a) hai làn cùng sửa `apps/web/**` ⇒ trong thời gian nới quyền làn B **không** đụng `apps/web/**` ngoài tệp sinh;
  (b) Gradle và `next build` chạy cùng lúc trên một máy (14 GB RAM, máy ảo) ⇒ không build web khi máy ảo đang chạy; (c) T013/T014
  cần API thật (`/v1/sim/*`, `/v1/graphs/incident`) ⇒ chỉ bắt đầu sau làn B 033 T011, trước đó chỉ T012 dựng từ fixture;
  (d) Playwright cần `HOICON_SIM_ENABLED=true` + gia đình demo trên DB `hoicon_android` ⇒ chạy `ops guardian_link --seed` ở DB đó.
- *Hết hạn:* tự hết khi 033 T016 xong hoặc khi làn A có việc Android mới; ghi vào `docs/HANDOFF.md` nếu Tiến duyệt.

**Wave 4 (xếp 23/10/2026, sau khi gộp Wave 3 `07c5816`).** Sửa các chỗ lệch spec mà hai làn ghi lại ở evidence. Đề xuất nới quyền làn A
cho web 033 (Wave 3) **chưa được duyệt** ⇒ làn B vẫn làm mọi `apps/web/**`.

| # | Làn A (Android) | Làn B (backend + web) |
|---|---|---|
| 1 | 031 **T014** — đồng bộ chuỗi `guardian_alerts` theo `2026.10-v4` (sha `afd2491…`), ghim lại sha | 024 **T020** (test đỏ) → **T021** (thứ tự ghép cố định, `ACTION_BUSY_VI`) |
| 2 | 010 **T029** — E7: "Vẫn tiếp tục" thành nút phụ, thân bài điều khiển từ xa thành 2 việc đánh số | 033 **T021** (`title_vi`, `is_sim`) → **T022** (web + token `sim.*`) → **T023** (dọn thiết bị `sim:`) |
| 3 | 011 **T022** — bố cục màn đồng ý (gợi ý cuộn "Xong rồi", nút "Mở cài đặt" lên trên, nhãn trạng thái ≥ 20sp) | 031 **T019** (`guidance` qua API) → **T020** (khối "Các bước nên làm" trên web) |
| 4 | 012 **T021** — kiểm mọi mẫu của `baseline-prof.txt` khớp ≥ 1 lớp, gọi từ release-gate | 012 **T020** — thử `roles.sql` trên Postgres tạm (đóng T017) |
| 5 | 032 **T011** — đo khoảng trống heartbeat (≳ 8 giờ, chạy nền khi làm 2–4) | Rà soát + cổng các spec Wave 3: 033 **T017 → T018 → T019 → T024**, 031 **T016**, 032 **T012 → T013** |
| 6 | 037 **T007** (sau làn B 037 T004) | 037 **T002 → T003 → T004 → T005 → T006** |

**Đối soát 24/10/2026 (nhà điều phối Opus, Tiến giao).** Hai làn đã đi trước kế hoạch: gộp `feat/w4-android`, `feat/w5-server`,
`feat/w5-android` vào `tien-collab-dev`. Wave 4 đã xong: A 031 T014; B 024 T020–T021, 011 T013/T014/T021, 012 T017 (Postgres tạm),
037 T001–T008 (theo bản nháp của làn B, đã đối soát), 050 giai đoạn 1 (T002–T010). Việc còn lại giao theo nhánh `feat/w6-*`:

| # | Làn A (`feat/w6-android`) | Làn B (`feat/w6-server`) |
|---|---|---|
| 1 | 010 **T029** → 011 **T022** → 012 **T021** | 012 **T020** (đối chiếu c584bea) → 033 **T021 → T022 → T023 → T024** |
| 2 | 032 **T011** (bộ đo dừng ở d_reboot, chạy nốt) | 031 **T019 → T020** |
| 3 | hc-api34 "Telecom không thấy cuộc gọi" + `fake_police --runs 10` (API 34, 36) | 037 **T013 → T014 → T009 → T016** |
| 4 | 050 **T014** | 050 **T016**; bộ kiểm cuối 033 T017/T019, 031 T016, 032 T012/T013, 050 T015 |

Hồ sơ thực thi: nhà điều phối = phiên Opus ở checkout chính; hai phiên Sonnet 5.5 (medium, tài khoản Orca `ngolamtien…` id `cd47ddcc`, mở lại 24/10 thay hai phiên cũ của tài khoản `towfienes…`) trong worktree `hoicon-wt/android`
và `hoicon-wt/server`, giao việc bằng nhập lệnh vào terminal Orca (**không** phải worker có giám sát: kiểm tiến độ bằng commit +
dòng `W6-A/W6-B XONG` + chạy lại Verify khi gộp). Trần 2 phiên ghi đồng thời; không thêm model/tài khoản dự phòng khi chưa hỏi Tiến.

**Wave 5 (tới đóng băng 06/01/2027).**

| # | Làn A | Làn B |
|---|---|---|
| 1 | 032 **T010** chỉ khi Minh bác I4 (đồng bộ lại `2026.10-v5`) | 037 **T008** (Android vitals) → **T009** (rà soát cuối toàn codebase) → **T010** |
| 2 | 011 **T012** sau khi Minh duyệt văn bản (011 T010) | 011 **T021** (kiểm đồng ý ở route đọc web) → **T020** (thực thi lời hứa khi tính năng có thật) |
| 3 | Việc máy thật khi có thiết bị/Firebase: 001 **T007–T010**, 029 **T012**, 012 **T015** | 024 **T016 → T017** chỉ khi Minh chọn F-1 = A (§8 mục 8) |
| 4 | Hỗ trợ quay video 5 phút (P2-21): 033 **T020** | 033 **T016** `/eval` web (danh sách cắt — cắt đầu tiên nếu trễ) |
| 5 | — | 037 **T011** chỉ khi Minh duyệt Crashlytics (§8 mục 13) |

**Wave 6 (sau nộp Vòng 2 09/01/2027, xong trước 07/02):** spec 050 **giai đoạn 2** (giai đoạn 1 làn B đã làm 23/10). Kiến trúc sư làm 050 **T001** (hợp đồng) ở checkout chính trước.
Làn B: **T002 → T003 → T004 → T005 → T006 → T008**; làn A: **T007** (`booth-record.py`) song song với T005; chung: **T009 → T010**.

**Việc chờ người (không xếp cho Sonnet):** 002 T024/T025 (token bot Zalo), 012 T010–T015 (VPS, Play Console), 029 T013 (ghi danh gia
đình thí điểm), 031 T017/T018, 032 T014/T015, 011 T010/T011, 036 kịch bản + cassette `recorded` (P0-08).

## 6. Cách làm một tính năng (bảng tra nhanh cho người và coding agent)
1. **Checkout chính:** lấy số spec ở §3; ROADMAP đổi task sang `◐`, thêm link `specs/NNN-slug` (sau khi thư mục tồn tại).
2. **Worktree/nhánh:** `git worktree add -b feat/NNN-slug ../hoicon-wt/<làn> origin/tien-collab-dev` (worktree đã có:
   `git switch -c feat/NNN-slug origin/tien-collab-dev`).
3. **Đặc tả** (phiên Claude trong worktree): `/speckit-specify` kèm `SPECIFY_FEATURE_DIRECTORY=specs/NNN-slug`, mã ROADMAP,
   US-xx, ADR → `/speckit-clarify` (nếu còn `[NEEDS CLARIFICATION]`) → `/speckit-plan` → `/speckit-tasks` →
   `/speckit-analyze` (0 CRITICAL/HIGH) → `/speckit-checklist privacy|elder-ux|release-block` khi liên quan.
4. **Làm:** `/speckit-implement` từng phase, chạy `Verify:` từng task → `/speckit-converge` tới 0 finding.
5. **Nghiệm thu:** cổng các tầng (§2.4 bước 4) → `evidence.md` → reviewer → `python3 scripts/check-spec-trace.py`.
6. **Tích hợp** (khi mọi task không bị chặn đã xong, evidence đủ, test xanh): commit trên nhánh spec → ở checkout chính
   `git merge --no-ff feat/NNN-slug` vào `tien-collab-dev` theo §5 luật 5 (cổng + gitleaks trước, push sau) → CI chạy trên
   Draft PR tổng (#12) → xanh thì xong spec. Bước 3–5 chạy một mạch theo §2.6, không có cổng duyệt giữa chừng. Còn task
   `BLOCKED` bởi bên ngoài ⇒ vẫn tích hợp, ROADMAP giữ `◐`, phần còn lại làm bằng nhánh lite nối tiếp khi gỡ chặn.
   **Cuối đợt:** bỏ Draft PR tổng (mô tả: link spec + evidence từng spec) → Minh review → merge `main` → ROADMAP `☑` cho
   spec đủ evidence → dọn worktree/nhánh.

Việc **lite**: bỏ bước 3–4 của Spec Kit, vẫn chạy test, vẫn ghi bằng chứng (trong `evidence.md` hoặc thông điệp commit).

## 7. Rủi ro chính
| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| 88 ngày tới Vòng 2 cho 2 người, phạm vi rất lớn | Cao | Theo đợt; danh sách cắt; làn H tách khỏi code; lite cho việc nhỏ |
| Play Console chậm xác minh ⇒ trượt M2 | Cao | Đăng ký tuần này; mượn hoặc mua máy thật |
| p95 ≤ 3 s không đạt trên máy thật | TB | O2/O3; dự phòng heads-up + giọng nói đã có |
| App ngân hàng thật phản ứng với quyền "hiển thị trên app khác" | TB | Giao thức S2 §5 trên máy thật; SAW thành tùy chọn |
| Hạn mức / điều khoản Zalo Bot | TB | `messages_out`; `/a/[token]` |
| Emulator Linux không ổn định khi headless | Thấp | `hw.gpu.mode=auto` (EMULATOR.md §1.2) |
| Spec Kit thành nghi thức tốn quota | TB | Làn lite; spec theo đợt; analyze/converge chỉ cho spec full |

## 8. Quyết định còn chờ (★ = Minh)
**Đã xong:**
- ☑ **D1** (spec 002, ADR-010): `chat_id` Zalo lưu mã hóa AES-256-GCM (khóa dữ liệu theo `kid`) + `zalo_user_hmac`
  (tiền tố `hoicon:zalo:v1:`) — **Tiến duyệt 15/10/2026**.
- ☑ **D2** (spec 002, ADR-010): migration `0003` tạo `families`, `members`, `pairing_codes`, `messages_out` —
  **Tiến duyệt 15/10/2026**. Spec 002 chạy một mạch từ T006 tới hết (§2.6).
- ☑ **O1** (+ B3): eval smoke làm trước 024 — **Tiến duyệt 15/10/2026, hoàn thành ở spec 030** (`hoicon-eval --suite smoke`,
  20 ca tất định, baseline `backend/eval/baseline.json`, bước CI trong `backend.yml`).
- ☑ **Quy trình tích hợp** — **Tiến chốt 15/10/2026**: spec merge thẳng vào `tien-collab-dev`, một Draft PR tổng (#12) lên
  `main` chạy CI liên tục, Minh nghiệm thu cuối đợt (§5 luật 5, §6 bước 6).

**Còn chờ:**
1. ★ I1, I2 vào 022/023; I3 spike sau M1; I4 gộp 032; I5 chỉ ở thuyết minh.
2. ★ B1 (tạo skill thiếu), B2 (bỏ mục cắt T2), B8 (cắt P1-S6 ngay).
3. ★ B4: hạ cam kết 50–100 gia đình hay nâng gate. ★ B6: cách chấm eval.
   (Spec 036 chấm hoàn toàn tất định + bộ kiểm thô `unsafe_advice`; LLM-judge để sau — đổi được nếu Minh chọn khác.)
4. ★ **Phạm vi `guardian_alerts` (DPIA)** — thêm 18/10/2026 khi dựng 031/032 và rà 011: một mục đích đồng ý có bao gồm cả (a) người
   giám hộ xem lại lịch sử trên web (027 — văn bản nháp nói "có"), (b) hồ sơ vụ việc soạn sẵn để con cháu mang đi trình báo (031 Q4),
   (c) bản tin tuần + báo "mất bảo vệ" dựa trên heartbeat (032 Q5)? **Đề xuất: có cả ba** (cùng người nhận, cùng dữ liệu, HỏiCon
   không chia sẻ thêm cho bên thứ ba), kèm câu chữ rõ trong văn bản. Nếu Minh tách: thêm giá trị enum + văn bản (luật 7); mã đã
   gom tên mục đích vào một hằng số (011 D9) nên đổi rẻ. Liên quan: rút `guardian_alerts` thì web còn hiện sự cố cũ không (011 T021,
   mặc định: không).
   **22/10:** chữ gộp đã chốt cho 031 T011 (160/160 từ) nói cả (a), (b), (c) trong một mục đích — tức là theo đề xuất "có cả ba";
   Minh tách thì văn bản phải tách theo.
5. ★ **I4 trong 032**: Tiến giao 032 "gồm I4" (18/10) trong khi mục 1 (I1–I5) chưa có ý kiến Minh. Phần "mất bảo vệ" nằm sau cờ
   `HOICON_PROTECTION_WATCH` (mặc định bật) — Minh từ chối thì tắt cờ, không gỡ mã. Văn bản `guardian_alerts` `2026.10-v4` (bản duy nhất, 031 T011) có câu "Họ được báo nếu HỏiCon bị tắt."; Minh từ chối ⇒ 032 T008 bỏ câu đó.
6. ★ **Kịch bản eval (036)** — cập nhật 22/10/2026: **cả 110 kịch bản** của suite full (60 cũ P1-07 + 50 mới do tác tử soạn) còn
   `draft: true`; Gate M3 chỉ là `pass` khi ≥ 100 ca được Minh duyệt bỏ `draft` **và** có cassette LLM thật (P0-08). Đọc trước
   nhóm `task_scam_*`, `recovery_scam_*`, `fake_bank_*` (security reviewer 036, Medium #4: mức chi tiết thủ đoạn). Kèm hai điểm
   nhỏ: 8 ca app ngoài Play có `min_risk_level: high` trong khi sàn ADR-001 là `critical` (nâng kỳ vọng hay giữ?); để kịp M3
   (09/01): khóa Anthropic cần có trước ~26/12.
7. **Tiến** (kỹ thuật, không phải ★): **trần cuộn 30 ngày của `/v1/lookups` (600 thiết bị / 600 người giám hộ / 3.000 gia đình) —
   đề xuất GIỮ, chờ Tiến xác nhận.** Lý do (`specs/026-verification-threat/plan.md` §10): giảm 3 lần sức dò bền bỉ so với trần ngày
   (1.800 ⇒ 600 lượt/thiết bị/tháng); dò cả danh sách 10.000 chỉ báo cần ≥ 140 "gia đình-tháng"; người dùng thật tra vài lần/tháng
   nên không chạm trần. Chú thích trong `backend/src/hoicon/api/routers/lookups.py` ghi "Tiến xác nhận" nhưng repo chưa có dấu vết
   ⇒ khi Tiến ghi "đồng ý" ở đây thì giữ chú thích; nếu đổi số thì sửa mã + chú thích cùng lúc.
8. ★ **F-1 (spec 024 §5, thêm 22/10/2026)**: người cao tuổi xác nhận "có người bảo chuyển tiền" ⇒ đồ thị luôn ép `critical`. Đúng
   luật (sàn tất định, LLM không hạ) nhưng báo nhầm chuyển tiền chính đáng: xấu nhất **10/37 = 0,27 > 0,10 ⇒ Gate M3 trượt** khi có
   model thật. **Đề xuất A**: hỏi thêm đúng một câu "bác có biết rõ người gọi không" chỉ trong nhánh này (tối đa 2 câu/sự cố);
   biết ⇒ `high`, không/không rõ/hết giờ ⇒ `critical` ⇒ xấu nhất 3/37 = 0,081. Giá: E8 thêm một câu (≤ 60 s); lừa đảo giả người
   thân mà người cao tuổi tin "biết người gọi" chỉ còn `high` (vẫn báo con, lời khuyên "gọi ngay" thay "gọi và giữ máy"). Phương án
   B (hạ sàn, để LLM quyết) không đề xuất; C (sửa kỳ vọng eval) bị loại vì giấu báo nhầm. Minh chọn A/B/giữ nguyên ⇒ ghi ở đây;
   chưa chọn thì 024 T016–T017 không chạy.
9. **Tiến**: chấp nhận **ADR-012** (tóm tắt người giám hộ từ danh sách điểm đóng — sửa F-2). Đây là rào an toàn thuộc nhóm "không
   bao giờ cắt" nên làn B thi công ngay theo bản Đề xuất (024 T014–T015); Tiến bác thì dừng ở T014 (test đỏ vẫn có giá trị).
10. **Tiến**: duyệt/bác **nới quyền làn A làm [B-web] của 033** (§5 "Wave 3": chỉ `apps/web/**`, không backend, không migration).
    Chưa duyệt ⇒ làn B tự làm, làn A rảnh sau 010 T028 tới khi 031 T011 xong.
11. ★ **Nguồn của 50 kịch bản mới (036)**: `source_ref` chỉ tái dùng nguồn của 60 kịch bản P1-07; **chưa ai mở lại các URL** (tác tử
    không truy cập mạng). Trước khi duyệt bỏ `draft` (mục 6): kiểm từng URL còn sống và đúng thủ đoạn, hoặc đổi nguồn.
12. ★ **Chữ màn đồng ý E3/E4/E10 (011, thêm 23/10/2026)** — đề xuất của `ux-elder-reviewer` (evidence 011, 22/10), duyệt cùng 011 T010;
    chữ nằm trong `docs/legal/consent/`, nên đổi chữ ⇒ tăng phiên bản ⇒ người đã đồng ý được hỏi lại (luật 7). Đề xuất: (a) E3 tách 3 ý
    có tiêu đề ngắn; (b) câu đường lui rõ hơn: "Bác muốn đổi ý lúc nào cũng được: nhờ người cài HỏiCon tắt giúp"; (c) bỏ cụm "để không bị
    kẻ xấu lợi dụng" ở E10. Phần bố cục (không đổi chữ) đã giao làn A: 011 T022.
13. ★ **Crashlytics (037, thêm 23/10/2026)**: gửi báo cáo lỗi app cho Google là **luồng dữ liệu mới cho bên thứ ba** ⇒ cần mục đích
    đồng ý + văn bản + DPIA + Play data safety (luật 7). **Đề xuất: chưa dùng**; đo độ ổn định bằng Android vitals của Play Console
    (không thêm SDK, 037 FR-008). Minh duyệt Crashlytics ⇒ 037 T011.
14. ★ **Link Zalo cũ sau khi rút `guardian_alerts` (037 FR-003, thêm 24/10/2026)**: làn B thi công mặc định D2 — `GET` trả "liên kết
    hết hạn" không kèm nội dung; `POST …/decision` vẫn ghi quyết định và đóng sự cố nhưng trả thân tối thiểu (đường an toàn: con bấm
    "đã gọi được bác" vẫn có tác dụng). Kiến trúc sư đề xuất giữ. Minh muốn chặn hẳn (403) ⇒ một task [B] đổi hằng số
    `WITHDRAWN_DECISION_POLICY` + test.
15. ★ **Đồng ý của người giám hộ (037 T009 Medium #4, thêm 24/10/2026)**: người giám hộ ghép qua Zalo được lưu `zalo_user_hmac` +
    `zalo_chat_enc` nhưng bảng `consents` chỉ có bản ghi của thiết bị người cao tuổi. Câu hỏi pháp lý: có cần bản ghi đồng ý riêng
    (mục đích mới + văn bản, luật 7) khi người giám hộ nhắn bot lần đầu không? Đề xuất: có, một câu đồng ý ngắn trong tin chào của
    bot + giá trị enum mới; làm trước thí điểm (G2). Minh quyết ⇒ kiến trúc sư viết spec nhỏ.
16. ★ **Chữ đồng ý — bổ sung cho mục 12 (24/10/2026, reviewer 011 W6):** thống nhất dấu nháy “ ” trong văn bản đồng ý; đoạn "Nhờ vậy…" đứng sau nút nên câu an toàn bị
    đẩy xuống — cân nhắc viết lại. Phần bố cục/nhãn không thuộc văn bản đồng ý đã giao làn A (011 T023).
