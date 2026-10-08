# HỏiCon — Lộ trình, mã task, gate

> Nguồn sự thật cho "làm gì tiếp". Chỉ làm task có mã trong file này; ý tưởng ngoài lề ghi vào **Ghi chú** cuối file.
> Trạng thái: `☐` chưa · `◐` đang làm · `☑` xong · `✂` đã cắt · `⏸` chờ Minh (tài khoản, quyết định).
> Hook SessionStart đọc khối STATUS dưới đây (≤ 6 dòng) — cập nhật mỗi khi đổi task.

<!-- STATUS -->
Phase 0 — Nền móng (08–14/10) · Gate G0: 14/10
Việc kế tiếp: P0-01
Đã xong: P0-02…P0-06 · Còn: P0-01 (repo GitHub + commit đầu), P0-07 (CI chạy xanh) · Chờ Minh: P0-08
Minh: khởi động lại Claude Code · gh auth login · đăng ký Play Console/Zalo Bot/Anthropic/Gemini/Firebase
Cập nhật: 08/10/2026
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
| P0-01 | git init, tái cấu trúc thư mục, `.gitignore/.gitattributes/.editorconfig`, chép pipeline thuyết minh vào `docs/proposal/src/`; repo GitHub riêng tư + `gh` | ◐ | `gh` 2.102 đã cài. Còn: `gh auth login` (Minh), tạo repo, commit đầu khi Minh yêu cầu — **nhớ `git add --chmod=+x apps/android/gradlew`** (repo `core.filemode=false`, thiếu bit thực thi ⇒ CI Linux lỗi) |
| P0-02 | Toolchain Android trên D: (JDK 21, SDK, Android CLI), WHPX, AVD hc-api36/34/29, `env-android.ps1`, smoke test máy ảo | ☑ | `docs/EMULATOR.md`; hc-api29 boot thử ở P1-S1 |
| P0-03 | Harness: plugin (ponytail, ui-ux-pro-max, official…), RTK, 7 hook + test, settings, `.mcp.json`, LSP; dọn settings cấp người dùng | ☑ | 49 test hook xanh; kotlin-lsp tắt (RAM); cần khởi động lại Claude Code — `docs/HARNESS.md` |
| P0-04 | `CLAUDE.md`, `AGENTS.md`, 8 subagent, 8 skill | ☑ | |
| P0-05 | Khung tài liệu: ROADMAP, ARCHITECTURE, DATA-MODEL, ADR-001…006, EMULATOR, HARNESS + stub PRD/API/AGENTS/DESIGN-SYSTEM/PRIVACY-DPIA/PLAY-POLICY/EVAL/PILOT-PROTOCOL | ☑ | + `docs/schemas/risk_event.v1.json` + fixture; stub được hoàn thiện theo task tương ứng |
| P0-06 | Khung chạy được: `infra/compose.dev.yml` (15432), backend `/healthz` + pytest + Alembic, `apps/web` (3100), `apps/android` `:app/:rules/:demobank`, `package.json` gốc (`dev:all`) | ☑ | `pnpm dev:all` ⇒ readyz 200 + web 200; backend 9 test; `:rules:test` (gồm test hợp đồng `rule_floor`); app hello cài trên hc-api36 |
| P0-07 | CI GitHub Actions: backend, web, android (lọc theo đường dẫn) + test hook | ◐ | 4 workflow đã viết (`.github/workflows/`); chạy xanh sau khi có repo |
| P0-08 | Tài khoản: Anthropic API (trần chi tiêu), Gemini, Zalo Bot Platform (`hoicon-dev`), **đăng ký Play Console ngay**, Firebase, cloudflared | ⏸ | cloudflared 2026.10 đã cài; còn lại Minh tự đăng ký; khóa để ở `backend/.env` / `D:\secrets` |

**Gate G0 (14/10)** — skill `phase-gate`:
- `pnpm dev:all` chạy DB + API + web; `GET :18000/healthz` = 200.
- 2–3 job CI xanh.
- App hello cài lên AVD `hc-api36` bằng skill `android-emulator-test`.
- `node --test ".claude/hooks/test/*.test.mjs"` xanh (gồm ca `READ_SMS` và số điện thoại thô bị chặn).
- SessionStart hiện STATUS.

## Phase 1 — Spike kỹ thuật + hồ sơ Vòng 1 (15/10–13/11)

| Mã | Việc | Thời gian | Ngưỡng đạt / sản phẩm | Trạng thái |
|---|---|---|---|---|
| P1-S1 | Cảm biến trên máy ảo: vai trò call screening, trạng thái cuộc gọi (`TelephonyCallback` vs `AudioManager`), FGS `specialUse` + chip "đang bảo vệ", quét UsageStats, mở SafePause qua miễn trừ "hiển thị trên app khác" | 15–24/10 | bắt 10/10 cuộc gọi; phát hiện → dừng p95 ≤ 3 s; sống sót khi app bị kill; có phương án dự phòng | ☐ |
| P1-S2 | Dừng an toàn với app ngân hàng: `:demobank`, phản ứng của app ngân hàng thật (Firebase Test Lab hoặc ghi rủi ro), full-screen intent Android 14 | 20–28/10 | bảng kết quả + `data/bank_apps.vn.json` v1 | ☐ |
| P1-S3 | Zalo Bot: webhook qua cloudflared, `/start <mã>`, nút bấm, đo hạn mức thật, điều khoản | 22–30/10 | giao tin p95 ≤ 5 s; chốt dự phòng (trang hành động / Telegram) | ☐ |
| P1-S4 | Lõi tác tử: đồ thị 2 interrupt + `AsyncPostgresSaver`, chạy tiếp sau `kill -9`, hẹn giờ bằng job, MCP `threat`, `agent_steps`, che PII, so Haiku 4.5 vs Flash-Lite | 26/10–04/11 | p95 một lượt ≤ 8 s; ghi chi phí | ☐ |
| P1-S5 | Giọng nói tiếng Việt: STT (`SpeechRecognizer` vi-VN, FPT.AI, Gemini) trên dữ liệu công khai + 20 câu tự thu; TTS giọng người già, 5 người nghe chấm | 28/10–08/11 | chốt nút bấm là chính, giọng nói tùy chọn; chọn nhà cung cấp âm thanh thu sẵn | ☐ |
| P1-S6 | Phát hiện cài app ngoài Play (R2) | nếu còn thời gian | | ☐ |
| P1-01 | Cập nhật thuyết minh qua `docs/proposal/src`: đội ngũ thật (1 người + đội tác tử AI + cố vấn), thí điểm 20–30 gia đình, Play testing, Zalo Bot | 26/10–08/11 | Word + PDF mới; `pitch-sync` sạch | ☐ |
| P1-02 | Khảo sát Google Form ≥ 300 phản hồi (tác tử soạn bảng hỏi, Minh phát tán) | 20/10–08/11 | báo cáo số liệu | ☐ |
| P1-03 | Video 3 phút trên máy ảo: cuộc gọi lạ → demobank → dừng an toàn có giọng nói → cảnh báo Zalo | quay 05–08/11 | file video | ☐ |
| P1-04 | `judge` chấm thử 10/11 → sửa → **nộp 13/11** | 10–13/11 | biên nhận nộp | ☐ |
| P1-05 | Design system: ui-ux-pro-max → `docs/DESIGN-SYSTEM.md` + `design-system/hoicon/tokens.json` (Be Vietnam Pro) | 14–22/11 | | ☐ |
| P1-06 | Văn bản đồng ý v1, DPIA rút gọn, quy trình thí điểm | 14–22/11 | `docs/legal/consent/`, `PRIVACY-DPIA.md`, `PILOT-PROTOCOL.md` | ☐ |
| P1-07 | ~60 kịch bản lừa đảo (tác tử soạn, Minh duyệt) | 14–22/11 | `data/scenarios/*.yaml` | ☐ |
| P1-08 | Kênh Play internal testing + Google Group tester | 14–22/11 | | ☐ |
| P1-09 | VPS + tên miền + Caddy | 14–22/11 | | ☐ |

**Gate G1 (08/11):** 5 báo cáo spike trong `docs/spikes/` (đi tiếp/không, có số đo); ADR-007…010; video xong.
**Cắt theo thứ tự:** P1-S6 → thu nhỏ P1-S5 → chỉ so 1 nhà cung cấp STT.

## Phase 2 — Lát dọc MVP (23/11–09/01)

| Mã | Tuần | Việc | Trạng thái |
|---|---|---|---|
| P2-01 | W1 23–29/11 | DB v1 + migration: families, members, devices, consents (trigger chỉ ghi thêm), trusted_contacts, pairing_codes, action_tokens | ☐ |
| P2-02 | W1 | Ghép đôi, xác thực thiết bị, API đồng ý; màn E1–E4 | ☐ |
| P2-03 | W1 | Nhận sự kiện theo lô (idempotent) + `IncidentService` state machine | ☐ |
| P2-04 | W1 | Triển khai VPS (`compose.prod.yml` + Caddy) + bot Zalo thí điểm | ☐ |
| P2-05 | W2 30/11–06/12 | Lính gác v1: CallScreening, cửa sổ rủi ro (FGS), UsageStats, luật R1, E7 SafePause + TTS | ☐ |
| P2-06 | W2 | E6 "Đang bảo vệ" + nút Hỏi con + hàng đợi gửi đi (Room) | ☐ |
| P2-07 | W2 | Cảnh báo giai đoạn 1 qua Zalo (mẫu) + trang hành động `/a/[token]` + quyết định người giám hộ → **M1** | ☐ |
| P2-08 | W3 07–13/12 | `risk_scorer` + ngân hàng câu hỏi + E8 qua FCM | ☐ |
| P2-09 | W3 | Tác tử can thiệp + interrupt `await_guardian` + hẹn giờ T1/T2/T3 | ☐ |
| P2-10 | W3 | `agent_steps` + luồng SSE trace | ☐ |
| P2-11 | W4 14–20/12 | Tác tử xác minh + MCP `threat` + E10 | ☐ |
| P2-12 | W4 | Web tối thiểu: danh sách/chi tiết sự cố cho người giám hộ | ☐ |
| P2-13 | W4 | Diễn tập v1 (E11, bảng `drills`) | ☐ |
| P2-14 | W4 | Bộ thí điểm + Play internal v0.3 → **M2** | ☐ |
| P2-15 | W5 21–27/12 | CLI `hoicon-eval` + ≥ 100 ca + chạy full lần đầu | ☐ |
| P2-16 | W5 | Nhánh hồ sơ vụ việc (`case_file`, interrupt duyệt) | ☐ |
| P2-17 | W5 | Đồ thị Coach hằng tuần | ☐ |
| P2-18 | W6 28/12–03/01 | Bộ eval injection + lặp prompt | ☐ |
| P2-19 | W6 | Web `/trace`, `/eval`, `/sim` | ☐ |
| P2-20 | W6 | Gia cố: `privacy-audit`, review bảo mật, job xóa theo hạn lưu, sao lưu, Crashlytics | ☐ |
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
| P4-02 | Chế độ gian: `/booth`, `/join/[code]`, `/demo/console`, demobank, phát lại khi mất mạng (xong trước 07/02) | ☐ |
| P4-03 | Slide 10 phút, poster, bộ câu hỏi phản biện | ☐ |
| P4-04 | Tổng duyệt 3 lần với `judge`; đóng băng 20/02 | ☐ |

**Gate G4 (26/02):** chạy gian 3 lần liên tiếp thành công, cảnh báo < 5 s; phát lại khi mất mạng hoạt động; có video dự phòng; reset demo < 1 phút.

## Ghi chú (ý tưởng ngoài phạm vi — không làm khi chưa có task)

- Mua máy Android cũ 1–2 triệu trước 06/12 (rủi ro #2) — Minh quyết.
- Đánh giá `android device remote` (Device Streaming, cần dự án Google Cloud) như nguồn máy thật bổ sung.
- Compose BOM ≥ 2026.08 (UI 1.12) và core-ktx 1.19 đòi **compileSdk 37** ⇒ hiện ghim BOM 2026.06.01. Khi cần: cài
  `platforms;android-37`, nâng compileSdk 37 (giữ targetSdk 36) — cân nhắc trước P2 (08/10, từ P0-06).
- RAM máy dev rất thấp (0,65–3 GB trống): chạy `scripts/stop-other-stacks.sh` (Minh đồng ý) trước khi làm máy ảo.
