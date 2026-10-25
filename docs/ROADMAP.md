# HỏiCon — Lộ trình, mã task, gate

> Nguồn sự thật cho "làm gì tiếp". Chỉ làm task có mã trong file này; ý tưởng ngoài lề ghi vào **Ghi chú** cuối file.
> Trạng thái: `☐` chưa · `◐` đang làm · `☑` xong · `✂` đã cắt · `⏸` chờ Minh (tài khoản, quyết định).
> Hook SessionStart đọc khối STATUS dưới đây (≤ 6 dòng) — cập nhật mỗi khi đổi task.
> Bản đồ tính năng ↔ spec ↔ phụ thuộc + cách làm (Spec Kit, worktree): `docs/MASTER-PLAN.md`. Task có spec thì dòng
> task ghi link `specs/NNN-slug` (kiểm bằng `python3 scripts/check-spec-trace.py`).

<!-- STATUS -->
Phase 1 — Spike + hồ sơ Vòng 1 (15/10–13/11) · G0 ĐẠT 08/10 · Gate G1: 08/11 · Đội: Minh + Tiến (@Towfienes)
25/10: Opus điều phối 2 Sonnet tới lượt 11 (tien-collab-dev 2c36457, pytest 2986): 037/033/031/032/026 gần đủ; spec mới 038 E12 (rút đồng ý, xóa có chờ 24 giờ hủy được); E7 release ≤ 3 s (API 34+36)
25/10 trưa: HẾT việc máy làm được (038 xong 8/8). Hồ sơ Vòng 1: pitch-sync + chấm thử judge (≈ 74/110) + kịch bản video ở `docs/proposal/` — chờ Minh sửa Word
Rủi ro: hồ sơ Vòng 1 chưa có commit trong `docs/proposal` (còn 21 ngày) · Play Console + Firebase + khóa API (W0-3/P0-08) chặn 001, M2, số M3
Chờ Minh: MASTER-PLAN §8 (I4, F-1, `guardian_alerts`, 110 kịch bản + nguồn, chữ đồng ý mục 12/16, Crashlytics, 14 link cũ, 15 đồng ý người giám hộ, 17 phạm vi xóa, 029 T009 tài liệu thí điểm) · Chờ Tiến: ADR-012, trần 30 ngày, push/PR, migration 0011–0015 ở prod
Cập nhật: 25/10/2026
<!-- /STATUS -->

## Mốc cứng

| Mốc | Ngày | Ghi chú |
|---|---|---|
| G0 — nền móng | 14/10/2026 | |
| G1 — spike + hồ sơ Vòng 1 | 08/11/2026 | `judge` chấm thử 10/11 |
| **Nộp Vòng 1** | **13/11/2026** (hạn 15/11) | thuyết minh + video 3 phút |
| Kết quả Vòng 1 (top 16) | 16–22/11/2026 | |
| M1 — luồng cảnh báo đầu–cuối | 06/12/2026 | |
| M2 — sẵn sàng thí điểm | 20/12/2026 | |
| Đóng băng code MVP | 06/01/2027 | |
| **Nộp Vòng 2 (M3)** | **09/01/2027** (hạn 10/01) | MVP + báo cáo thí điểm + poster + video 5 phút |
| G3 — thí điểm Tết | 14/02/2027 | |
| Đóng băng chung kết | 20/02/2027 | |
| G4 — sẵn sàng gian | 26/02/2027 | |
| **Chung kết** | **27/02/2027** | bình chọn tại gian = 30% |

## Phase 0 — Nền móng (08–14/10)

| Mã | Việc | Trạng thái | Ghi chú |
|---|---|---|---|
| P0-01 | git init, tái cấu trúc thư mục, `.gitignore/.gitattributes/.editorconfig`, chép pipeline thuyết minh vào `docs/proposal/src/`; repo GitHub (public — Minh chọn 08/10) + `gh` | ☑ | Repo public `bminhnemhoi/TechStarUp_TDTU2027_HoiCon`; PR #1 bootstrap (squash `b9e8dc9`) + PR #2 siết quyền (`ad685e4`); gitleaks + quét số điện thoại/email sạch; `gradlew` + `*.sh` có bit thực thi |
| P0-02 | Toolchain Android trên D: (JDK 21, SDK, Android CLI), WHPX, AVD hc-api36/34/29, `env-android.ps1`, smoke test máy ảo | ☑ | `docs/EMULATOR.md`; hc-api29 boot thử ở P1-S1 |
| P0-03 | Harness: plugin (ponytail, ui-ux-pro-max, official…), RTK, 7 hook + test, settings, `.mcp.json`, LSP; dọn settings cấp người dùng | ☑ | 64 test hook xanh; quyền đã siết (PR #2); kotlin-lsp tắt (RAM); cần khởi động lại Claude Code — `docs/HARNESS.md` |
| P0-04 | `CLAUDE.md`, `AGENTS.md`, 8 subagent, 8 skill | ☑ | |
| P0-05 | Khung tài liệu: ROADMAP, ARCHITECTURE, DATA-MODEL, ADR-001…006, EMULATOR, HARNESS + stub PRD/API/AGENTS/DESIGN-SYSTEM/PRIVACY-DPIA/PLAY-POLICY/EVAL/PILOT-PROTOCOL | ☑ | + `docs/schemas/risk_event.v1.json` + fixture; stub được hoàn thiện theo task tương ứng |
| P0-06 | Khung chạy được: `infra/compose.dev.yml` (15432), backend `/healthz` + pytest + Alembic, `apps/web` (3100), `apps/android` `:app/:rules/:demobank`, `package.json` gốc (`dev:all`) | ☑ | `pnpm dev:all` ⇒ readyz 200 + web 200; backend 9 test; `:rules:test` (gồm test hợp đồng `rule_floor`); app hello cài trên hc-api36 |
| P0-07 | CI GitHub Actions: backend, web, android (lọc theo đường dẫn) + test hook | ☑ | PR #1: **5/5 job xanh** — backend (27s), android (2m04s), web (35s), harness (8s), secrets/gitleaks (6s). Đã sửa: tag `setup-uv@v10` không tồn tại; hook loop factory trả None trên Linux. Action ghim SHA + Dependabot |
| P0-08 | Tài khoản: Anthropic API (trần chi tiêu), Gemini, Zalo Bot Platform (`hoicon-dev`), **đăng ký Play Console ngay**, Firebase, cloudflared | ⏸ | Hướng dẫn từng bước: `docs/setup/ACCOUNTS.md`. Claude đã làm: `gh` đăng nhập, cloudflared 2026.10, `init_env`/`check_keys`. Play Console cá nhân cần xác minh bằng **máy Android thật** (mượn được) trước P1-08 |

**Gate G0 (14/10)** — skill `phase-gate`:
- `pnpm dev:all` chạy DB + API + web; `GET :18000/healthz` = 200.
- 2–3 job CI xanh.
- App hello cài lên AVD `hc-api36` bằng skill `android-emulator-test`.
- `node --test ".claude/hooks/test/*.test.mjs"` xanh (gồm ca `READ_SMS` và số điện thoại thô bị chặn).
- SessionStart hiện STATUS.

## Phase 1 — Spike kỹ thuật + hồ sơ Vòng 1 (15/10–13/11)

| Mã | Việc | Thời gian | Ngưỡng đạt / sản phẩm | Trạng thái |
|---|---|---|---|---|
| P1-S1 | Cảm biến trên máy ảo: vai trò call screening, trạng thái cuộc gọi (`TelephonyCallback` vs `AudioManager`), FGS `specialUse` + chip "đang bảo vệ", quét UsageStats, mở SafePause qua miễn trừ "hiển thị trên app khác" | 15–24/10 | bắt 10/10 cuộc gọi; phát hiện → dừng p95 ≤ 3 s; sống sót khi app bị kill; có phương án dự phòng | ◐ cơ chế chốt (ADR-007): bắt 10/10, offline OK, không cần READ_PHONE_STATE; Android 15+ cần tắt tối ưu pin. **p95 ≤ 3 s chưa đạt trên máy ảo quá tải ⇒ đo máy thật (Firebase Test Lab) trước G1** **15/10 (spec 001, `specs/001-safe-pause-real-device`):** máy ảo hc-api36/34, 2 biến thể E7: p95 1 370–1 790 ms (n = 10 nguội + 10 ấm) — số máy ảo, không kết luận; **máy thật BLOCKED: chưa có Firebase (W0-3) + `gcloud`**; chưa hoàn thành |
| P1-S2 | Dừng an toàn với app ngân hàng: `:demobank`, phản ứng của app ngân hàng thật (Firebase Test Lab hoặc ghi rủi ro), full-screen intent Android 14 | 20–28/10 | bảng kết quả + `data/bank_apps.vn.json` v1 | ◐ ADR-008 + `docs/spikes/P1-S2-dung-an-toan.md`: danh sách v1 **50 gói** (sinh `BankAppCatalog` + `<queries>`, test chống lệch); `:demobank` có luồng chuyển tiền đầy đủ; FSI **không dùng** ở bản phát hành (máy mở khóa ⇒ heads-up; Play giới hạn); app ngân hàng thật **không thử được trên máy ảo/FTL** (TT 77/2025 ⇒ sổ rủi ro RB-1…9 + giao thức máy thật sau P1-08); bộ đo `:latency` cho FTL. Còn: ảnh demobank + `ux-elder-reviewer`, đo FSI trên AVD, chạy FTL **15/10 (spec 001, `specs/001-safe-pause-real-device`):** FSI đã đo trên AVD 34/36 (heads-up, ADR-008 q.1 giữ nguyên); demobank hết chồng dòng ở 200% + ảnh qua `ux-elder-reviewer` (0 High demobank); TTS AVD Linux sửa bằng môi trường (`docs/EMULATOR.md`). **Còn: FTL máy thật BLOCKED (Firebase)**; chưa hoàn thành |
| P1-S3 | Zalo Bot: webhook qua cloudflared, `/start <mã>`, nút bấm, đo hạn mức thật, điều khoản | 22–30/10 | giao tin p95 ≤ 5 s; chốt dự phòng (trang hành động / Telegram) | ◐ `specs/002-zalo-guardian-channel` + ADR-010 (D1/D2 Tiến duyệt 15/10) + `docs/spikes/P1-S3-zalo.md`: code + test xong ở chế độ mock (webhook, ghép `/start`, phản hồi 1/2/3, hạn mức, lệnh ops); Zalo **không có nút bấm** và **không có `update_id`**. **BLOCKED: chờ token bot thật (W0-3)** để đo SC-001 và hạn mức thật; chưa đánh dấu hoàn thành |
| P1-S4 | Lõi tác tử: đồ thị 2 interrupt + `AsyncPostgresSaver`, chạy tiếp sau `kill -9`, hẹn giờ bằng job, MCP `threat`, `agent_steps`, che PII, so Haiku 4.5 vs Flash-Lite | 26/10–04/11 | p95 một lượt ≤ 8 s; ghi chi phí | ◐ ADR-009 + `docs/spikes/P1-S4-loi-tac-tu.md`: đồ thị 2 interrupt + T1/T2/T3, sống sót kill -9 (test), job chống trùng, MCP `threat` tại `/mcp/threat`, `agent_steps` + chi phí, che PII, không lưu lời kể thô/h1 (review bảo mật đã sửa hết); 86 test xanh. Điều phối p50 0,13 s/lượt (p95 máy dev bị swap ⇒ đo lại trên VPS). **Chờ khóa API (P0-08)** để so Haiku 4.5 / **Haiku 5.5** (rẻ hơn 10×, mặc định tạm) / Flash-Lite. **Spec [`003-agent-core-mcp-threat`](../specs/003-agent-core-mcp-threat/) đã hiện thực (15/10, chưa merge; 607 test xanh, bằng chứng ở `evidence.md`):** `threat_indicators` chỉ HMAC (migration `0004`) + lệnh nạp, MCP `threat` có token Bearer + giới hạn tần suất (kéo sớm từ P2-11; vẫn chưa mở ra Internet — 012), `spike bench --model --json`, trần chi tiêu đọc `agent_steps` (bền qua khởi động lại). **Còn BLOCKED:** bảng so Haiku 4.5 vs 5.5 có khóa thật (P0-08) và đo p95 trên VPS (P1-09) ⇒ vẫn ở trạng thái dở dang (◐) |
| P1-S5 | Giọng nói tiếng Việt: STT (`SpeechRecognizer` vi-VN, FPT.AI, Gemini) trên dữ liệu công khai + 20 câu tự thu; TTS giọng người già, 5 người nghe chấm | 28/10–08/11 | chốt nút bấm là chính, giọng nói tùy chọn; chọn nhà cung cấp âm thanh thu sẵn | ◐ 15/10 (`specs/004-voice-vi`, `docs/spikes/P1-S5-giong-noi.md`; thu nhỏ: chỉ `SpeechRecognizer` trên máy, ≥ 3 người nghe): đo trên 2 máy ảo — TTS vi-VN offline có (6 giọng/AVD), p95 ấm ≤ 3 ms, nguội + khởi tạo ≤ 411 ms; STT trên máy chỉ có vi-VN ở API 36 (bộ tổng hợp WER 7,2 %, ý định 12/12), API 34 chỉ có bộ mặc định dùng mạng. Quyết định theo quy tắc đăng ký trước: STT = MVP chỉ nút bấm (thiếu bản thu đội); TTS đường chính chưa chốt (thiếu điểm nghe). **Còn: bản thu của đội, ≥ 3 người nghe, máy thật — BLOCKED**; chưa hoàn thành |
| P1-S6 | Phát hiện cài app ngoài Play (R2) | nếu còn thời gian | | ☐ |
| P1-01 | Cập nhật thuyết minh qua `docs/proposal/src`: đội ngũ thật (1 người + đội tác tử AI + cố vấn), thí điểm 20–30 gia đình, Play testing, Zalo Bot | 26/10–08/11 | Word + PDF mới; `pitch-sync` sạch | ◐ 25/10 đối chiếu cam kết + đề xuất câu chữ: [`docs/proposal/PITCH-SYNC-2026-10-25.md`](proposal/PITCH-SYNC-2026-10-25.md) — chờ Minh quyết B4/B5 rồi sửa Word |
| P1-02 | Khảo sát Google Form ≥ 300 phản hồi (tác tử soạn bảng hỏi, Minh phát tán) | 20/10–08/11 | báo cáo số liệu — bảng hỏi v1: `docs/research/survey/P1-02-bang-hoi.md` (Minh dựng Google Form + phát tán) | ◐ |
| P1-03 | Video 3 phút trên máy ảo: cuộc gọi lạ → demobank → dừng an toàn có giọng nói → cảnh báo Zalo | quay 05–08/11 | file video | ◐ 25/10 kịch bản đối chiếu sản phẩm thật: [`docs/proposal/VIDEO-V1-SCRIPT.md`](proposal/VIDEO-V1-SCRIPT.md) — người quay |
| P1-04 | `judge` chấm thử 10/11 → sửa → **nộp 13/11** | 10–13/11 | biên nhận nộp | ☐ |
| P1-05 | Design system: ui-ux-pro-max → `docs/DESIGN-SYSTEM.md` + `design-system/hoicon/tokens.json` (Be Vietnam Pro) | 14–22/11 | | ◐ spec [`specs/010-design-system/`](../specs/010-design-system/) (kéo sớm 15/10): **đã làm** `tokens.json` → `Tokens.kt` + `colors.xml` + `tokens.css` (26 cặp ≥ 7:1/3:1 có test), font đóng gói trong APK, E7 vẫn 10/10 trên máy ảo; **còn** FR-013 (`ux-elder-reviewer` còn 2 High về E7 ở 200% màn nhỏ ⇒ P2-05, xem Ghi chú) — chưa hoàn tất. **Wave 3 (22/10):** T028 chốt chữ E7 điều khiển từ xa (bỏ "Kẻ gian", tiêu đề ngắn) + chụp lại hc-api36/34 ⇒ đóng T027 |
| P1-06 | Văn bản đồng ý v1, DPIA rút gọn, quy trình thí điểm | 14–22/11 | `docs/legal/consent/`, `PRIVACY-DPIA.md`, `PILOT-PROTOCOL.md` | ◐ spec [`011-consent-legal`](../specs/011-consent-legal/) (18/10): **bản nháp** 10 văn bản (1/mục đích) + `manifest.json` (phiên bản, sha256) + `ops/consent_texts.py` + test enum↔văn bản↔sha256 (41 test, đột biến 14/14), DPIA rút gọn, PILOT-PROTOCOL; `ux-elder-reviewer` 4 Chặn (đều là `llm_processing`/`voice_input`/`pilot_research`: **hứa điều mã chưa thực thi**), 6 Cao đã sửa chữ; **chờ Minh duyệt**, người thật đọc thử, làn A đồng bộ chuỗi Android (danh sách ở `evidence.md`) |
| P1-07 | ~60 kịch bản lừa đảo (tác tử soạn, Minh duyệt) | 14–22/11 | `data/scenarios/*.yaml` | ◐ bản nháp 60 ca (40 lừa đảo / 20 hợp lệ song sinh = 33%, 10 chèn lệnh, 3 miền, nguồn báo chí đã kiểm) + schema `scenario.v1.json` + test hợp đồng — **chờ Minh duyệt** (`draft: true`) |
| P1-08 | Kênh Play internal testing + Google Group tester | 14–22/11 | | ◐ spec [`012-release-and-hosting`](../specs/012-release-and-hosting/) (FR-011, làn A; sửa phạm vi 18/10 theo `/speckit-analyze`): bản `release` 0.3.0 có R8 + `release-gate.sh` ĐẠT cục bộ (`3129dd3`); **còn**: buildType `demo` + baseline profile (T016), đo khởi động nguội AVD (T018); **BLOCKED**: AAB đã ký lên Play internal + Google Group (T015, Play Console W0-3) |
| P1-09 | VPS + tên miền + Caddy | 14–22/11 | | ◐ spec [`012-release-and-hosting`](../specs/012-release-and-hosting/): Caddy + `compose.prod.yml` + script triển khai **dựng và thử trên máy dev** (xem P2-04); **BLOCKED**: VPS + tên miền + Let's Encrypt thật (T010) |

**Gate G1 (08/11):** 5 báo cáo spike trong `docs/spikes/` (đi tiếp/không, có số đo); ADR-007…010; video xong.
**Cắt theo thứ tự:** P1-S6 → thu nhỏ P1-S5 → chỉ so 1 nhà cung cấp STT.

## Phase 2 — Lát dọc MVP (23/11–09/01)

| Mã | Tuần | Việc | Trạng thái |
|---|---|---|---|
| P2-01 | W1 23–29/11 | DB v1 + migration: families, members, devices, consents (trigger chỉ ghi thêm), trusted_contacts, pairing_codes, action_tokens | ☑ spec [`020-family-pairing-consent`](../specs/020-family-pairing-consent/) (kéo sớm Đợt 4, 16/10): migration `0005`, trigger `prevent_consent_tamper` append-only |
| P2-02 | W1 | Ghép đôi, xác thực thiết bị, API đồng ý; màn E1–E4 | ☑ spec [`020-family-pairing-consent`](../specs/020-family-pairing-consent/) (kéo sớm Đợt 4, 16/10): API `POST /v1/pair` + `/v1/consents`, luồng Android E1–E4 (E3 Prominent Disclosure Google Play) |
| P2-03 | W1 | Nhận sự kiện theo lô (idempotent) + `IncidentService` state machine | ☑ spec [`021-events-incident-service`](../specs/021-events-incident-service/) (kéo sớm Đợt 5, 16/10): migration `0006`, POST /v1/events idempotent lô 1–50, IncidentService state machine với advisory lock và optimistic version, 965 tests |
| P2-04 | W1 | Triển khai VPS (`compose.prod.yml` + Caddy) + bot Zalo thí điểm | ◐ spec [`012-release-and-hosting`](../specs/012-release-and-hosting/) (viết ngược 18/10): **hạ tầng xong và thử trên máy dev** (`compose.prod.yml`, `Caddyfile`, 2 Dockerfile, `deploy-vps.sh`, `backup-vps.sh`, `VPS-DEPLOYMENT.md`, 26 test hạ tầng, đột biến 19/19); review bảo mật 0 Critical/High, 2 Medium đã sửa (tách mạng web, timeout Caddy), 12 Low ở `evidence.md`; **BLOCKED**: VPS + tên miền + Let's Encrypt thật, bot Zalo thật + `setWebhook`, chép sao lưu ra ngoài máy, giám sát `/readyz`, áp `roles.sql`; phần Android thuộc làn A (`P1-08`) |
| P2-05 | W2 30/11–06/12 | Lính gác v1: CallScreening, cửa sổ rủi ro (FGS), UsageStats, luật R1, E7 SafePause + TTS | ☑ spec [`022-sentinel-v1`](../specs/022-sentinel-v1/) (kéo sớm Đợt 5, 16/10): cửa sổ rủi ro 600s, luật R1 (ngân hàng) & R5 (remote control), E7 SafePause Compose + TTS offline (còn FTL máy thật) |
| P2-06 | W2 | E6 "Đang bảo vệ" + nút Hỏi con + hàng đợi gửi đi (Room) | ☑ spec [`022-sentinel-v1`](../specs/022-sentinel-v1/) (kéo sớm Đợt 5, 16/10): Room DB + Tink AEAD outbox, E6 Đang bảo vệ, nút Hỏi con, kết nối POST /v1/events |
| P2-07 | W2 | Cảnh báo giai đoạn 1 qua Zalo (mẫu) + trang hành động `/a/[token]` + quyết định người giám hộ → **M1** | ☑ spec [`023-guardian-alert`](../specs/023-guardian-alert/) (kéo sớm Đợt 6, 16/10): cảnh báo mẫu qua Zalo (token `/a/` sinh lúc gửi, chỉ lưu SHA-256), trang `/a/[token]`, quyết định qua liên kết/JWT/Zalo 1-2 (nghi lừa đảo ⇒ `case_open`), `scripts/e2e-m1.sh` phần máy chủ (còn: p95 Zalo thật, chặng Android ↔ máy chủ) |
| P2-08 | W3 07–13/12 | `risk_scorer` + ngân hàng câu hỏi + E8 qua FCM | ◐ spec [`024-risk-and-intervention`](../specs/024-risk-and-intervention/) (kéo sớm Đợt 7, 16/10): ngân hàng câu hỏi E8 (công khai AI), API pending-question/answers, E8 Compose + WorkManager, câu trả lời nâng mức tất định; còn: FCM thật (P0-08) + đường mở E8 trên máy |
| P2-09 | W3 | Tác tử can thiệp + interrupt `await_guardian` + hẹn giờ T1/T2/T3 | ◐ spec [`024-risk-and-intervention`](../specs/024-risk-and-intervention/) (kéo sớm Đợt 7, 16/10): đồ thị tự chạy từ `/v1/events` (worker trong API), T1/T2/T3 tôn trọng quyết định ngoài đồ thị, kết quả ghi qua IncidentService; còn: tóm tắt p95 với LLM thật. **Wave 3 (22/10):** T014–T015 + T018–T019 sửa F-2 (tóm tắt từ danh sách điểm đóng, ADR-012 đề xuất); T016–T017 F-1 ★ chờ Minh (MASTER-PLAN §8 mục 8) |
| P2-10 | W3 | `agent_steps` + luồng SSE trace | ◐ spec [`025-trace-sse`](../specs/025-trace-sse/) (16/10): **đã làm** `GET /v1/runs/{id}/steps`, `/v1/runs/{id}/stream` (SSE), `/v1/incidents/{id}/run` (JWT người giám hộ), `redact_json` + danh sách trắng cột (không `input_redacted`), trần 20 luồng/3 mỗi người, client TS sinh lại; SC-001 p95 ≈ 0,30 s trên uvicorn thật (localhost); **còn** giao diện tiêu thụ (027/033) và đo `: ping` qua Caddy (012) — giữ ◐ |
| P2-11 | W4 14–20/12 | Tác tử xác minh + MCP `threat` + E10 | ☑ 25/10 tasks đủ (T031 bộ kiểm cả hai làn); spec [`026-verification-threat`](../specs/026-verification-threat/): **làn B (server) xong** (`/v1/lookups`, node `verification` tất định, `threat-list` bucket k-ẩn danh — ADR-011 **chấp nhận 18/10**, MCP `threat`); 18/10: T029 client TS + T030 review bảo mật lượt 2 (0 Critical/High, 3 Medium **đã sửa**: trần 30 ngày chống dò danh sách, 503 khi giải mã `bucket_enc` hỏng, rút đồng ý `lookups` làm sạch dấu vết; 14 Low ở `evidence.md`); **còn**: làn A (T020–T028: `ThreatBucketIndex`, Room v2, `ThreatSyncWorker`, E10, E2E máy ảo) và T031 |
| P2-12 | W4 | Web tối thiểu: danh sách/chi tiết sự cố cho người giám hộ | ☑ spec [`027-guardian-web`](../specs/027-guardian-web/) (16/10, chưa commit): đăng nhập bằng liên kết một lần qua Zalo (lệnh "4", **Zalo mock**), cookie `hc_guardian` + CSRF, `/v1/guardian/*`, 4 trang web + trace trực tiếp (`EventSource`); 6/6 SC đạt trên localhost (pytest 1597, Playwright 58 + live 264 ms ≤ 1 s, axe 0 lỗi); review bảo mật 0 High, UX 0 Chặn (4 Cao đã sửa); **còn**: Zalo thật, Caddy/012, các mục Medium ở Ghi chú (g–k) |
| P2-13 | W4 | Diễn tập v1 (E11, bảng `drills`) | ◐ spec [`028-drills`](../specs/028-drills/) (16/10): Làn A (E11 Compose, DrillEngine, workers) và Làn B (migration 0008, drill_service, API drills, guard D2) đã xong code & test; chờ E2E và Minh duyệt 3 kịch bản |
| P2-14 | W4 | Bộ thí điểm + Play internal v0.3 → **M2** | ◐ spec [`029-pilot-kit`](../specs/029-pilot-kit/) (17/10): **làn B giai đoạn 1 XONG** (migration 0010 `device_heartbeats`, `POST /v1/heartbeat`, hạn lưu 90 ngày, `ops pilot enroll/report/gate-m2`, schema `heartbeat.v1`/`pilot_report.v1`, client TS, docs); pytest 2017 xanh; **còn**: làn A (T005 phân biệt 403 `consent_withdrawn`, test ghim fixture), T008 `release-gate.sh`, T009 tài liệu thí điểm, giai đoạn 2 chờ 012 + W0-3 |
| P2-15 | W5 21–27/12 | CLI `hoicon-eval` + ≥ 100 ca + chạy full lần đầu | ◐ 23/10: CLI + smoke 20 ca + **full 110 ca** ([`specs/036-eval-full`](../specs/036-eval-full/), 28/28 task): sau F-2 (ADR-012) recall 100% / báo nhầm 0% / 0 vi phạm / công khai AI 100%, không lệch `baseline-full` — **số rào tất định** trên cassette `synthetic`, 110/110 kịch bản `draft`, chưa phải số M3; còn: CI xanh trên PR, Minh duyệt kịch bản + nguồn (MASTER-PLAN §8 mục 6, 11), cassette `recorded` (P0-08) |
| P2-16 | W5 | Nhánh hồ sơ vụ việc (`case_file`, interrupt duyệt) | ◐ spec [`031-case-file`](../specs/031-case-file/) (24/10: 18/20 task; `guidance` lên web, bộ kiểm cuối ĐẠT; còn T017 người giám hộ thí điểm duyệt + T018 Minh duyệt `report_guidance`)
| P2-17 | W5 | Đồ thị Coach hằng tuần | ◐ spec [`032-coach-weekly`](../specs/032-coach-weekly/) (24/10: 12/15 task; T011 heartbeat 5 điều kiện trên máy ảo hc-api36, khoảng trống dài nhất 22,1 phút ≪ ngưỡng 24 giờ; T012/T013 ĐẠT; còn T010 (chỉ khi Minh bác I4), T014 thí điểm, T015 Minh duyệt tips)
| P2-18 | W6 28/12–03/01 | Bộ eval injection + lặp prompt | ◐ 23/10: `hoicon-eval --suite injection` **17/17 ca bị chặn, 0 vi phạm** sau F-2 (ADR-012, spec 024 T014–T015 + 036 T025–T028: tóm tắt chỉ ghép câu cố định, kiểm `brief_outside_vocabulary`); Wave 4: 024 T020–T021 thứ tự ghép cố định; F-1 (024 T016–T017) ★ chờ Minh; **lặp prompt bằng LLM thật BLOCKED** (P0-08) |
| P2-19 | W6 | Web `/trace`, `/eval`, `/sim` | ◐ spec [`033-web-sim-eval`](../specs/033-web-sim-eval/) (24/10: 23/24 task: `/sim`, `/trace`, `/eval` (P3, chưa chia theo nhóm/miền), `title_vi`/`is_sim`, dọn thiết bị `sim:`, SIM.md + quickstart; còn T020 quay video P2-21)
| P2-20 | W6 | Gia cố: `privacy-audit`, review bảo mật, job xóa theo hạn lưu, sao lưu, Crashlytics | ◐ E12 rút đồng ý/xóa dữ liệu từ app: spec [`038-settings-privacy`](../specs/038-settings-privacy/) (25/10: 8/8 task XONG trên máy ảo; số đo ở evidence) · spec [`034-hardening-core`](../specs/034-hardening-core/) lõi XONG; [`037-hardening-rest`](../specs/037-hardening-rest/) 24/10: 19/21 (ép manifest, đồng ý lúc gửi, IDOR, sao lưu khóa con + restore một giao dịch, thu hồi phiên (0013), DPIA/BACKUP/STABILITY; rà soát cuối 0 Critical/0 High, certifi CVSS 9.1 đã nâng); còn T011 Crashlytics (chờ Minh), T021 phần SIM xong
| P2-21 | W7 04–09/01 | Đóng băng 06/01; báo cáo thí điểm; poster; video 5 phút; **nộp 09/01** → **M3** | ☐ |

**Gate M1 (06/12):** AVD API 34 + 36: cuộc gọi lạ → demobank → SafePause p95 ≤ 3 s · Zalo giai đoạn 1 p95 ≤ 10 s · thao tác người giám hộ đóng được sự cố · mỗi quyền đã cấp có dòng consent · **0 số điện thoại thô** trong DB/log · backend tắt vẫn hiện SafePause.
**Gate M2 (20/12):** ≥ 5 gia đình đã cài, **≥ 1 máy thật** · heartbeat ≥ 90% · crash-free ≥ 99% · LLM quá hạn ⇒ rơi về mẫu · 0 lỗi bảo mật High.
**Gate M3 (09/01):** eval ≥ 100 ca (≥ 30% cuộc gọi hợp lệ, ≥ 10 injection): recall leo thang ≥ 0,90; leo thang nhầm ≤ 0,10; **0 vi phạm an toàn**; công khai AI 100% · tóm tắt giai đoạn 2 p95 ≤ 15 s · ≥ 20 gia đình đăng ký, ≥ 20 buổi diễn tập · cố gắng ≥ 1 LOI.

**Danh sách cắt (theo thứ tự):** cá nhân hóa Coach → DOCX hồ sơ vụ việc → giao diện `/eval` → dashboard web ngoài danh sách sự cố → trả lời bằng giọng nói → chuyển người giám hộ thứ hai → Langfuse → luật R2 → MCP `docs`/`voice`/`scenario` (thành tool nội bộ).
**Không bao giờ cắt:** sổ đồng ý · công khai AI · che PII · dừng an toàn · đường cảnh báo · trace · eval ≥ 100 ca.

## Phase 3 — Thí điểm + eval (14/12–14/02)

| Mã | Việc | Trạng thái |
|---|---|---|
| P3-01 | Đợt 1: gia đình Minh, họ hàng, bạn học (cài qua video call có hướng dẫn) | ☐ |
| P3-02 | Diễn tập theo `docs/PILOT-PROTOCOL.md` (khung giờ đã đồng ý, ≤ 2 lần/tháng, cơ quan hư cấu, debrief) | ☐ |
| P3-03 | Chiến dịch Tết 25/01–14/02 "Tết này, hỏi con trước khi chuyển tiền" | ☐ |
| P3-04 | Báo cáo số liệu v2: kích hoạt, thời gian onboarding, giữ quyền 7/14 ngày, phát hiện khi diễn tập, tỷ lệ vượt qua, thời gian phản hồi người giám hộ, báo nhầm/gia đình-tuần | ☐ |

**Gate G3 (14/02):** ≥ 30 gia đình đăng ký, ≥ 50 buổi diễn tập, báo cáo v2. Chỉ tuyên bố số có đo.

## Phase 4 — Hoàn thiện chung kết (11/01–27/02)

| Mã | Việc | Trạng thái |
|---|---|---|
| P4-01 | Sửa theo góp ý BGK Vòng 2 | ☐ |
| P4-02 | Chế độ gian: `/booth`, `/join/[code]`, `/demo/console`, demobank, phát lại khi mất mạng (xong trước 07/02) | ◐ spec [`050-booth-mode`](../specs/050-booth-mode/) (24/10: giai đoạn 1 XONG — `/booth`, `/demo/console`, phát lại khi mất mạng, `ops booth reset`; hợp đồng giai đoạn 2 đã có (`sim_reset`, `booth_join`), `/join/[code]` đang làm; demobank tại gian (T014) làn A)
| P4-03 | Slide 10 phút, poster, bộ câu hỏi phản biện | ☐ |
| P4-04 | Tổng duyệt 3 lần với `judge`; đóng băng 20/02 | ☐ |

**Gate G4 (26/02):** chạy gian 3 lần liên tiếp thành công, cảnh báo < 5 s; phát lại khi mất mạng hoạt động; có video dự phòng; reset demo < 1 phút.

## Ghi chú (ý tưởng ngoài phạm vi — không làm khi chưa có task)

- **(Spec 027, web người giám hộ — 16/10/2026):** (a) chọn **shadcn/ui** để dành cho 033 (dashboard nhiều thành phần); 027
  chỉ dùng Tailwind + `tokens.css`. (b) **012 (Caddy/VPS) phải che `/login/*` và `/a/*` trong log truy cập** và để `/v1/*`
  đi thẳng tới API hoặc qua Next (đã đo: rewrite của Next không đệm/nén SSE). (c) Cookie phiên chỉ có cờ `Secure` khi
  `HOICON_ENV` ∉ {dev, test, ci}: ở prod **bắt buộc đặt `HOICON_ENV`** (mặc định là `dev`) và `HOICON_WEB_BASE_URL`/`HOICON_WEB_ORIGINS`.
  (d) Phiên JWT 7 ngày chỉ thu hồi bằng xóa thành viên (không có danh sách đen); cân nhắc thu hồi theo phiên nếu thí điểm cần.
  (e) Người giám hộ trên web chưa có đường ghi đồng ý `lookups` (tra cứu E10 của 026 vẫn 403 cho họ). (f) Rewrite `/v1/*` của
  web cố định lúc `next build` (`HOICON_API_URL`).
  Từ review bảo mật 027 (0 Critical/High): (g) **cân nhắc đổi liên kết thành `/login#<token>`** (fragment không bao giờ tới
  server/proxy/log/Referer và không nằm trong payload RSC; hiện theo spec là đường dẫn `/login/<token>` + 15 phút + một lần +
  `no-referrer` + `no-store`); (h) **thu hồi phiên thật** (cột phiên/`jti` ⇒ cần migration, ngoài phạm vi 027) và cho vòng lặp
  SSE kiểm lại thành viên/`exp` mỗi ~60 s (trace_service, 025); (i) **hỏi Minh/DPIA**: đồng ý `guardian_alerts` có bao gồm việc
  người giám hộ XEM LẠI lịch sử/trace trên web không (nếu không ⇒ thêm giá trị enum + kiểm đồng ý ở route đọc, luật 7);
  (j) web nhận cả `device_id`, `opened_by_event_id`, `drill_id`, `version` của người được bảo vệ dù không dùng: nên có model riêng
  cho web; (k) từ review UX 027 còn lại (Trung bình/Thấp): sự cố `case_open` chưa có nút "đã rõ an toàn" trên web (cần quy tắc
  chuyển trạng thái ở 031), đổi từ "sự cố" thành "cảnh báo" cho đồng nhất với Zalo, màu nút khóa đạt 7:1.

- **E7 ở cỡ chữ 200% trên màn nhỏ (từ spec 010, 15/10 — vào P2-05, E7 SafePause; `ux-elder-reviewer`):** (High)
  hàng "Đây là trợ lý AI HỏiCon" + nút "Nghe lại" ép câu công khai AI thành 3 dòng hẹp; vùng cuộn chỉ còn ~2 dòng thân (~1 dòng
  khi đang giữ nút) trên AVD API 34 vì thanh nút ghim cao ~37% màn hình ⇒ cần bố cục riêng cho `fontScale ≥ 1,5` (xếp dọc không
  đủ vì "Nghe lại" cao ≥ 64dp; cân nhắc rút gọn dòng trạng thái/để trạng thái cuộn cùng nội dung). (Medium/Low, cần quyết định
  thiết kế) khoảng cách từ hẹp ở Be Vietnam Pro 400 ("như một"), cân nhắc đóng gói thêm Medium 500 hoặc `letterSpacing`; nhắc
  "vuốt lên để đọc tiếp"; tên mục "Quyền truy cập dữ liệu sử dụng" thành 2 dòng; chụp thêm trạng thái "✗ Chưa bật" của màn quyền;
  nút "Gọi cho con" hiện ≈ 60dp vì inset MaterialButton (đã có từ spec 001). Ảnh: `~/hoicon-evidence/010-design-system/shots/`.
- (spec 003) `threat_indicators` chỉ lưu HMAC ⇒ chưa đồng bộ được danh sách xuống máy (máy so **h1**). 022/026 phải chọn:
  cột `value_enc` AES-256-GCM (như D1 của 002) hay danh sách h1 tách khỏi DB.
- (spec 003, từ review bảo mật 15/10 — chưa làm, cần task riêng): (a) chỉ mục `agent_steps(at)` (migration mới) cho phép
  tính trần chi tiêu khi bảng lớn; (b) `/readyz` báo thiếu pepper/danh sách đe dọa trống (lỗi tra cứu hiện chỉ có log
  `warning` ⇒ danh sách có thể tê liệt không ai biết); (c) tra cứu ở prod lọc `is_demo = false` hoặc đưa `is_demo` vào
  `ThreatVerdict`; (d) lệnh gỡ số bị gắn cờ nhầm + thủ tục ở `PRIVACY-DPIA`; (e) `list_version` của `unknown` so chuỗi
  (dùng `max(last_seen)`); (f) `candidate_hmacs` cố định kid 1–2; (g) eval `--shared-db-ok` để lại dòng demo ở DB dùng chung.
- **Ý tưởng 15/10 (chờ Minh duyệt — MASTER-PLAN §4):** I1 luật R5 app điều khiển từ xa trong cửa sổ cuộc gọi lạ ⇒
  `critical` (vào P2-05, bổ sung ADR-001) · I2 câu nhắc "mật khẩu gia đình" ở E7/E9 (không lưu mật khẩu) · I3 nhận biết
  cuộc gọi Zalo/Messenger (`MODE_IN_COMMUNICATION`) — spike sau khi có máy thật · I4 tin Zalo hằng tuần + báo "mất bảo
  vệ" (gộp P2-17) · I5 giọng con thu sẵn — chỉ ghi vào thuyết minh.
- **Điểm bất hợp lý cần quyết (MASTER-PLAN §1):** B1 skill `state-transition`/`consent-copy` + `PiiMasker` chưa có ·
  B2 "chuyển người giám hộ thứ hai" trong danh sách cắt nhưng đã code ở P1-S4 · B3 eval smoke nên làm trước P2-08 ·
  B4 thuyết minh hứa 50–100 gia đình, gate chỉ ≥ 20/30 · B5 đội 2 người + nhóm sinh viên · B6 provider cho `judge` ·
  B7 Play Console là đường găng M2 · B8 cắt P1-S6 ngay.
- Mua máy Android cũ 1–2 triệu trước 06/12 (rủi ro #2) — Minh quyết. Trước mắt: mượn máy người thân để xác minh Play
  Console (< 1 phút); kiểm thử máy thật qua Firebase Test Lab (5 lượt/ngày) + Device Streaming (30 phút/tháng).
- (P1-S2) Danh mục v2: cân nhắc thêm app Smart OTP tách riêng của ngân hàng (RB-7); hỏi thí điểm về "ứng dụng kép"
  Xiaomi (RB-6). `:demobank` chưa mô phỏng "đăng xuất khi chạy nền" — thêm nếu giao thức máy thật cho thấy app phổ
  biến làm vậy (RB-4).
- Đánh giá `android device remote` (Device Streaming, cần dự án Google Cloud) như nguồn máy thật bổ sung.
- Compose BOM ≥ 2026.08 (UI 1.12) và core-ktx 1.19 đòi **compileSdk 37** ⇒ hiện ghim BOM 2026.06.01. Khi cần: cài
  `platforms;android-37`, nâng compileSdk 37 (giữ targetSdk 36) — cân nhắc trước P2 (08/10, từ P0-06).
- RAM máy dev rất thấp (0,65–3 GB trống): chạy `scripts/stop-other-stacks.sh` (Minh đồng ý) trước khi làm máy ảo.
- **Chặn phát hành (review 09/10):** KHÔNG đưa bản build nào cho người thật (closed testing, thí điểm, gian trưng bày)
  trước khi có: E3 công bố nổi bật + bản ghi đồng ý có phiên bản (P2-02), Room + Tink thay SharedPreferences (P2-05),
  buildType `demo`/release với R8 + log chẩn đoán tắt (P1-08). Bản spike chỉ dùng trên máy ảo/máy dev.
- (Spec 025) `agent_runs.incident_id` **không được ghi** khi `IncidentRuntime` tạo lượt (liên kết sự cố ↔ lượt chỉ là
  `thread_id = str(incident.id)`). Luồng truy vết dựa vào `thread_id`; nên ghi cột này (và thêm FK) khi sửa runtime ở
  spec tác tử kế tiếp. Cùng chỗ: lượt kẹt `running` khi node ném lỗi (chỉ `recover()` lúc khởi động đặt `failed`) ⇒ luồng
  SSE không có `done`, chỉ đóng theo `MAX_STREAM_S`.
- (Spec 025, review) `mask_text` chưa gộp dấu `,`/`:` giữa các nhóm số (`0900,000,123` ⇒ lộ 6 số cuối); lớp che `output` dựa vào
  danh sách đen khóa — khi thêm node mới nên chuyển sang danh sách trắng khóa theo từng node. Trần luồng chưa có giới hạn tần
  suất mở luồng/đăng ký gia đình; `uvicorn --timeout-graceful-shutdown` cần đặt ở lệnh chạy (012).
- (Spec 025, review lượt 3) `mask_text` còn lộ 6 số cuối khi số điện thoại ngăn bằng `, ; : * |` có dấu cách (`0900, 000, 123`);
  `redact_json` không bắt token base64 chuẩn có `/` hay token < 32 ký tự, và khóa viết liền (`phonenumber`) — lớp thật sự chặn
  vẫn là danh sách trắng cột `step_view` + khóa cấm; node mới ghi vào `agent_steps.output` nên dùng khóa/giá trị enum.
