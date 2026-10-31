# Bằng chứng nghiệm thu: Dừng an toàn — số đo máy thật và hoàn tất spike S1/S2

**Spec**: `specs/001-safe-pause-real-device/spec.md` · **Mã ROADMAP**: P1-S1, P1-S2 · **Nhánh/PR**: feat/001-safe-pause-real-device · chưa commit/PR · **Ngày**: 15/10/2026

> **Spec CHƯA hoàn tất, không được đánh ☑:** SC-001 (máy thật) **BLOCKED — chưa có tài khoản Firebase (W0-3, Minh) và `gcloud` chưa cài**
> ⇒ T007–T010 chưa làm. Mọi số bên dưới là số **máy ảo** (Linux headless, bản debug, `compile=speed`); không dùng để kết luận máy thật.
> Bằng chứng thô (ảnh, log, công cụ chụp/đo) nằm ngoài repo: `~/hoicon-evidence/001-safe-pause-real-device/{shots,logs,tools}` (viết tắt `$EV`).
> Nhãn nguồn dùng trong bảng: **AVD** = máy ảo hc-api36 (Android 16) / hc-api34 (Android 14) trên máy Linux của Tiến.

## Tiêu chí thành công (SC) ↔ số đo

| SC | Ngưỡng | Đo được | Môi trường (máy ảo / FTL / máy thật, n) | Đạt? | Bằng chứng |
|---|---|---|---|---|---|
| SC-001 | p95 `app_foreground → pause_shown` ≤ 3 000 ms, nguội + ấm, máy thật FTL (Samsung A Android 14, Pixel Android 15/16), n ≥ 10 | **BLOCKED** — không có số máy thật. Số máy ảo tham khảo: p95 1 370–1 790 ms (n = 10 mỗi ô, 2 AVD × 2 biến thể × nguội/ấm) | máy thật FTL: chưa chạy (thiếu Firebase + `gcloud`); máy ảo AVD hc-api36/34, n = 10 | **BLOCKED** (không đánh ✓ cho máy thật) | `docs/spikes/device-matrix.md` (dòng 15/10/2026 + dòng BLOCKED); `$EV/logs/lat{34,36}-{view,compose}.log` |
| SC-002 | bộ đo đủ mốc ≥ 19/20 mỗi biến thể mỗi AVD | 20/20 ở cả 4 ô: hc-api36 view, hc-api36 compose, hc-api34 view, hc-api34 compose (nguội 10/10 + ấm 10/10) | máy ảo AVD hc-api36 và hc-api34, n = 20 mỗi ô | ✓ | `$EV/logs/lat36-view.log`, `lat36-compose.log`, `lat34-view.log`, `lat34-compose.log` |
| SC-003 | thông báo dự phòng + câu nói đầu ≤ 3 000 ms từ `app_foreground`, ≥ 4/5 lần khi thu hồi SAW | 5/5 ở mỗi máy ảo. api34: thông báo 1 639–2 408 ms, câu nói 1 643–2 410 ms; api36: thông báo 2 042–2 423 ms, câu nói 2 045–2 539 ms. Luôn là thông báo nổi (heads-up), `fsi=true` nhưng `topResumedActivity` vẫn là demobank | máy ảo AVD hc-api34 và hc-api36, n = 5 mỗi máy, máy mở khóa | ✓ | `$EV/logs/fsi34.txt`, `fsi36.txt`; ảnh `$EV/shots/fsi-api34-*.png` |
| SC-004 | `ux-elder-reviewer` không còn mục High với bộ ảnh 100%/200% | Không còn High thuộc demobank. Còn 1 High thuộc E7 (nút "Gọi cho con" ≈ 60 dp < 64 dp) ⇒ chuyển P2-05 (ngoài phạm vi spec). 3 Medium demobank còn tồn (xem "Còn tồn") | ảnh 2 cỡ chữ (100%, 200%) × 2 AVD × 7 màn = 28 ảnh, máy ảo hc-api36 + hc-api34 | ✓ (cho phạm vi spec: demobank) | `$EV/shots/{api36,api34}-{100,200}-*.png`, `montage-*.png`, ảnh lỗi trước sửa `before-api36-200-transfer.png`; báo cáo reviewer dưới mục Review |
| SC-005 | `emu-scenario.py fake_police` bắt 10/10 và `:rules:test` xanh sau mọi thay đổi | api36: 10/10 ĐẠT, SafePause p50 878 p95 1 724 ms; api34: 10/10 ĐẠT, SafePause p50 641 p95 2 563 ms (lần đầu của lô chậm 2 563 ms). `:rules:test` 54/54 (gồm `AiDisclosureCopyTest`), `:app:lintDebug :demobank:lintDebug` xanh | máy ảo AVD hc-api36 và hc-api34, n = 10 mỗi AVD (chạy sau thay đổi cuối của demobank) | ✓ | `$EV/logs/final36.txt`, `final34.txt` |
| SC-006 | `tts_started` ở ≥ 9/10 lần màn dừng hiện | api36: 10/10 (câu nói đầu 357–1 094 ms); api34: 10/10 sau khi cài lại dữ liệu giọng (trước đó 0/10: `tts error`) | máy ảo AVD hc-api36 và hc-api34 (Linux), n = 10 mỗi AVD | ✓ | `$EV/logs/final36.txt`, `final34.txt`, `tts34-after.txt`; `docs/EMULATOR.md` §1.2 |

Đường cơ sở trước khi sửa (T002, cùng quy trình): api36 10/10 hiện SafePause (p50 537, p95 1 387 ms; 1/10 cây UI thiếu chữ "gọi cho con" ⇒ script báo TRƯỢT, mốc `pause_shown` vẫn đủ); api34 lô đầu 0/10 vì script chẩn đoán "Telecom không thấy cuộc gọi đến (lỗi modem giả lập)", sau boot `--cold` 10/10 (p50 670, p95 1 800 ms). Log: `$EV/logs/baseline36.txt`, `baseline34.txt` (bản sau boot cold).

## Yêu cầu chức năng (FR) ↔ test

| FR | Test / cách kiểm | Kết quả |
|---|---|---|
| FR-001 | `:latency:connectedDebugAndroidTest` (variant view + compose, runs=10) trên hc-api36 và hc-api34 | ✓ 20/20 mỗi ô, xuất `latency.json` (logcat `HC_LATENCY`) |
| FR-002 | `scripts/ftl-latency.sh` trên FTL ≥ 2 máy thật | **BLOCKED** — chưa có Firebase/`gcloud` (T007, T008) |
| FR-003 | tham số `variant=view|compose`, mỗi lô tự loại lượt có `safe pause ui=` lệch; `ftl-latency.sh --variant` | ✓ cho máy ảo (cả hai biến thể đo xen cùng bản cài); phần máy thật BLOCKED |
| FR-004 | ghi `docs/spikes/device-matrix.md` + `P1-S2-dung-an-toan.md` §3/§7: loại máy, model, Android, ngày, n, nguồn | ✓ cho máy ảo; dòng máy thật ghi BLOCKED |
| FR-005 | kết luận gate P1-S1 bằng số máy thật; đề xuất cập nhật ADR-007 | **BLOCKED** (T010) — xem "Đề xuất ADR" dưới đây; chưa sửa file ADR |
| FR-006 | `$EV/tools/fsi.py` (SAW deny, n = 5 mỗi AVD): loại hiển thị, `fsi=`, thời gian thông báo + câu nói đầu | ✓ SC-003; ghi vào P1-S2 §3 mục 4 |
| FR-007 | ảnh 200% màn chuyển tiền: trước (`before-…`) chồng dòng, sau (`api36-200-3-…`, `api34-200-3-…`) không chồng; `:demobank:lintDebug` | ✓ (sửa `lineHeight` Title/Body/Primary/Secondary, `demobank/MainActivity.kt`) |
| FR-008 | bộ ảnh 100%/200% × 2 AVD × 7 màn (đăng nhập, trang chủ, chuyển tiền, xác nhận, OTP, kết quả, dừng an toàn) + `ux-elder-reviewer` | ✓ không còn High thuộc demobank |
| FR-009 | chẩn đoán R3 + sửa môi trường + hướng dẫn `docs/EMULATOR.md` §1.2; `Speaker.kt` không đổi | ✓ api34 `tts_started` 10/10; nguyên nhân: gói giọng vi-VN hỏng (`Failed to load pipeline definitions`, status -4) |
| FR-010 | `emu-scenario.py` 10/10 hai AVD sau thay đổi; manifest release không có INTERNET; không đổi code `:app` | ✓ |
| FR-011 | `:app:processReleaseMainManifest` + grep manifest đã merge (release: `USE_FULL_SCREEN_INTENT` 0, `ScenarioReceiver` 0, `INTERNET` 0; debug: có cả hai). `DUMP` ở release chỉ là receiver của AndroidX ProfileInstaller | ✓ |

## Cổng các tầng (lệnh đã chạy)

| Tầng | Lệnh | Kết quả |
|---|---|---|
| Backend | — (làn A, không đụng `backend/**`) | SKIPPED: ngoài phạm vi |
| Android | `apps/android/gradlew -p apps/android :rules:test :app:testDebugUnitTest :app:lintDebug :demobank:lintDebug` | ✓ BUILD SUCCESSFUL; 54 test, 0 lỗi |
| Android (build) | `:app:assembleDebug :demobank:assembleDebug :latency:assembleDebug` | ✓ |
| Web | — | SKIPPED: ngoài phạm vi |
| Hook | — | SKIPPED: không đổi hook |
| Máy ảo | `python scripts/emu-scenario.py --avd hc-api36|hc-api34 --scenario fake_police --runs 10` | ✓ 10/10 và 10/10 (cuối cùng, sau mọi thay đổi code) |
| Eval | `run-eval smoke` | SKIPPED: không đổi agent/prompt |
| Truy vết | `python3 scripts/check-spec-trace.py` | ✓ "check-spec-trace: 1 spec, 0 lỗi" (sau khi ghi evidence.md + ROADMAP) |
| Chưa chạy | AVD API 29 (`emu-scenario.py`) | SKIPPED: DoD yêu cầu API 36 và 34 |

## Review

| Reviewer | Kết quả | Đã xử lý |
|---|---|---|
| `security-privacy-reviewer` | 0 Critical/High. 1 Medium: CI kiểm manifest release (`.github/workflows/android.yml:49`) chưa chặn `INTERNET`/`READ_PHONE_STATE`/`RECORD_AUDIO`… (có từ trước, ngoài phạm vi). 4 Low: (2) kiểm cờ bằng `ls <tệp>` mong manh; (3) `@After` không thu hồi appops; (4) thiếu cảnh báo "chỉ chạy trên AVD/FTL"; (5) `--variant=X` không nhận | (2) **đã sửa** (liệt kê thư mục thay vì tệp) và chạy lại 3 lượt × 2 biến thể trên api34 xanh; (4) **đã thêm** cảnh báo vào `docs/EMULATOR.md`; (1) ghi "Còn tồn"; (3), (5) bỏ qua có chủ đích (ảnh hưởng chỉ máy ảo/FTL, không phải lỗi) |
| `ux-elder-reviewer` | 0 High demobank. 3 Medium demobank: cuộn dùng chung giữa các màn; nhãn "Nội dung chuyển tiền" bể dòng ở api34-200; mã OTP "246 810" tách dòng. 1 High E7: nút "Gọi cho con" ≈ 60 dp; Medium E7: khối nút ghim chiếm ~28% màn ở 200%, câu công khai AI bị bóp ở api34-200 | Medium demobank → "Còn tồn" (video P1-03 nên sửa trước khi quay); các mục E7 → P2-05 (spec 022) |
| `/ponytail-review` (tự thực hiện, đọc `git diff` + code liên quan) | 1 điểm cần sửa: kiểm cờ `variant` bằng `ls files/<cờ>` có thể báo oan nếu stderr trộn stdout. Không có chỗ thừa/dư; thay đổi nhỏ (≈ +30 dòng bộ đo, +13 dòng script, 5 chỗ `lineHeight`) | Đã sửa như trên |

## `/speckit-converge`

1 vòng, 0 finding cần thêm task: đối chiếu FR/SC/US/plan/constitution với mã hiện có. Phần chưa làm duy nhất là T007–T010 (FTL), **bị chặn bên ngoài** (tài khoản Firebase, `gcloud`) ⇒ theo MASTER-PLAN §2.5 ghi BLOCKED ở đây, không thêm task mã. `tasks.md` không có phần Convergence. Phát hiện phụ: `quickstart.md` grep sai tag log (`fsi=` nằm ở `HC_SPIKE`) — đã sửa.

## Đề xuất cập nhật ADR (chưa sửa file ADR; Minh duyệt rồi sửa qua PR riêng)

- **ADR-007, mục "Chưa chốt"**: *giữ nguyên trạng thái "chưa đóng"*. Chỉ nên thêm một dòng số máy ảo: "15/10/2026, máy ảo Linux hc-api36/34, bản debug, `compile=speed`, n = 10 nguội + 10 ấm: p95 1 370–1 790 ms cho cả View và Compose; không dùng để kết luận (ADR-008: máy ảo không đại diện máy thật)". Đóng mục chỉ sau khi có số FTL (T007–T010).
- **ADR-008, quyết định 1 (không dùng FSI ở bản phát hành)**: số đo xác nhận — máy mở khóa chỉ hiện heads-up dù `fsi=true`, trên Android 14 và 16; chưa kiểm máy đang khóa và máy thật. Đề xuất ghi "đã xác nhận trên máy ảo 15/10/2026".
- Chưa có đề xuất đổi quyết định về View/Compose: hai biến thể chênh ≤ ~200 ms trên máy ảo; chọn ở P2-05 theo số máy thật.

## Còn tồn / hoãn có chủ đích

- **T007–T010 BLOCKED**: cần tài khoản Firebase (W0-3, Minh) + cài `gcloud`; hạn mềm 05/11 (spec "Ngoài phạm vi"). Chạy: `bash scripts/ftl-latency.sh --variant view|compose model=…,version=…` (4 lượt Spark: 2 máy × 2 biến thể). Nếu tới 05/11 chưa có: thuyết minh chỉ dùng số máy ảo kèm nhãn "máy ảo".
- demobank (3 Medium từ `ux-elder-reviewer`): `rememberScrollState` dùng chung giữa các màn; nhãn ô "Nội dung chuyển tiền" bể dòng ở 200%; mã OTP nên tách dòng riêng + dấu cách không ngắt. Không thuộc FR nào của spec; nên sửa trước khi quay video (P1-03).
- E7: nút "Gọi cho con" < 64 dp, khối nút ghim chiếm nhiều màn ở 200%, câu "Đây là trợ lý AI HỏiCon" bị bóp ở api34-200 ⇒ **P2-05 / spec 022**.
- CI: `android.yml` nên chặn thêm `INTERNET`, `READ_PHONE_STATE`, `RECORD_AUDIO`, `PROCESS_OUTGOING_CALLS`, `MANAGE_EXTERNAL_STORAGE` trong manifest release (Hiến chương I) — ngoài phạm vi làn A/worktree này, đề nghị ghi vào "Ghi chú" ROADMAP qua checkout chính.
- Ghi nhận môi trường: sau `:latency:connectedDebugAndroidTest`, `:app` bị gỡ ⇒ phải cài lại + cấp vai trò/quyền; `com.android.cli.interact.instrumentation` còn sót làm `UiAutomationService already registered` — đã ghi vào `docs/EMULATOR.md`.
- Số máy ảo của 15/10 thấp hơn nhiều lô 08/10 (p95 5–10 s); chưa đo RAM host nên không khẳng định nguyên nhân. Máy ảo ≠ máy thật.
