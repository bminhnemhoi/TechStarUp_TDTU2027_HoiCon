---

description: "Tasks for spec 001 — Dừng an toàn: số đo máy thật và hoàn tất spike S1/S2"
---

# Tasks: Dừng an toàn — số đo máy thật và hoàn tất spike S1/S2

**Input**: `/specs/001-safe-pause-real-device/` (spec.md, plan.md, research.md, quickstart.md, contracts/)

**Tests**: bắt buộc. Spec này chủ yếu là đo đạc ⇒ "test" = lệnh đo/hồi quy có số, ghi vào evidence.md.

**Làn**: A (Android) — worktree `../hoicon-wt/android`. Không sửa `backend/**`, `apps/web/**`, `docs/schemas/**`.
Một emulator mỗi lúc; không chạy Gradle song song với làn B.

## Format: `[ID] [P?] [Story] Description — FR-xxx · Verify: \`lệnh\``

---

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Khởi động AVD và build nền: `bash scripts/emu-start.sh hc-api36 --headless`; build `:app :demobank :latency` debug; ghi trạng thái quyền + miễn tối ưu pin — FR-010 · Verify: `apps/android/gradlew -p apps/android :rules:test :app:assembleDebug :demobank:assembleDebug` xanh
- [x] T002 Hồi quy trước khi sửa (đường cơ sở): `python scripts/emu-scenario.py --avd hc-api36 --scenario fake_police --runs 10`, lặp với hc-api34 — FR-010 · Verify: 10/10 bắt được mỗi AVD, số ghi vào evidence.md

---

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T003 Thêm arg `variant=view|compose` vào apps/android/latency/src/main/java/vn/hoicon/latency/SafePauseLatencyTest.kt: trước mỗi lô `run-as vn.hoicon.sentinel touch|rm -f files/spike_compose_pause`; ghi `variant` vào `latency.json` và log; lần đo có `safe pause ui=` lệch `variant` ⇒ không hợp lệ (research R1) — FR-003 · Verify: `apps/android/gradlew -p apps/android :latency:assembleDebug` (`:latency` là module `com.android.test` tự đo — không có task `assembleDebugAndroidTest`). Lưu ý: `mkdir -p files` trước `touch` vì thư mục `files/` chưa chắc đã tồn tại trên máy sạch
- [x] T004 Truyền `variant` trong scripts/ftl-latency.sh bằng cờ riêng `--variant view|compose` (mặc định `view`; các tham số `model=…,version=…` vẫn là thiết bị) → `--environment-variables runs=10,compile=speed,variant=…`; thêm ví dụ chạy 2 biến thể vào phần chú thích đầu file — FR-002, FR-003 · Verify: `bash -n scripts/ftl-latency.sh`

**Checkpoint**: bộ đo chọn được biến thể — US1 bắt đầu được

---

## Phase 3: User Story 1 - Biết chắc màn dừng hiện kịp trên máy thật (Priority: P1) 🎯 MVP

**Goal**: số p50/p95 nguội/ấm trên ≥ 2 máy thật, cả hai biến thể E7; kết luận gate P1-S1

**Independent Test**: đọc `latency.json` của 4 lượt FTL; so ngưỡng 3 s

### Tests for User Story 1 ⚠️

- [x] T005 [US1] Chạy bộ đo trên AVD hc-api36 cho `variant=view` và `variant=compose` (10 nguội + 10 ấm mỗi biến thể) — FR-001 · Verify: `apps/android/gradlew -p apps/android :latency:connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.variant=view` (rồi `compose`) — đọc `latency.json`: đủ mốc ≥ 19/20 mỗi chế độ (SC-002); nếu test đỏ chỉ vì 1 lần thiếu mốc thì ghi nguyên nhân vào evidence.md, không sửa test
- [x] T006 [US1] Lặp T005 trên AVD hc-api34 — FR-001 · Verify: như T005 với hc-api34

### Implementation for User Story 1

- [ ] T007 [US1] FTL Samsung dòng A Android 14: `bash scripts/ftl-latency.sh model=<samsung-a>,version=34` cho 2 biến thể (2 lượt Spark); tải `latency.json` + log `HC_LATENCY` — FR-002, FR-003 · Verify: kết quả có đủ mốc; nếu chưa có Firebase ⇒ ghi `BLOCKED: chưa có tài khoản Firebase (W0-3)` trong evidence.md
- [ ] T008 [US1] FTL Pixel Android 15/16: như T007 — FR-002, FR-003 · Verify: như T007
- [ ] T009 [US1] Ghi số vào docs/spikes/device-matrix.md (dòng "máy thật": model, Android, ngày, n, p50/p95, biến thể) và docs/spikes/P1-S2-dung-an-toan.md §3 hạng mục 5 + §7 — FR-004 · Verify: review (mỗi dòng có nguồn FTL/AVD + ngày + n)
- [ ] T010 [US1] Kết luận gate P1-S1: cập nhật mục "Kết luận"/"Chưa chốt" của docs/spikes/P1-S1-cam-bien.md và **đề xuất** cập nhật ADR-007 mục "Chưa chốt" bằng số đo (đổi trạng thái theo số, không đổi quyết định cơ chế): ghi đề xuất (đoạn văn thay thế) trong P1-S1-cam-bien.md và evidence.md, **không sửa file ADR** (Minh duyệt và sửa ADR qua PR riêng) — FR-005 · Verify: review; nếu T007/T008 BLOCKED thì task này cũng BLOCKED

**Checkpoint**: US1 có số máy thật (hoặc BLOCKED được ghi rõ)

---

## Phase 4: User Story 2 - Dự phòng khi không có quyền hiển thị trên ứng dụng khác (Priority: P2)

**Goal**: xác nhận heads-up + giọng nói, ghi hành vi FSI trên Android 14/16

**Independent Test**: thu hồi SAW, chạy kịch bản, đọc mốc trong log

- [x] T011 [US2] AVD hc-api34: `appops set vn.hoicon.sentinel SYSTEM_ALERT_WINDOW deny`, chạy `emu-scenario.py --scenario fake_police --runs 5`, ghi loại hiển thị, `fsi=` (log `HcSpikeLog` dòng `fallback notification fsi=…`), thời gian tới thông báo (hiệu của mốc epoch logcat `-v epoch` của dòng đó và mốc `app_foreground`) và `tts_started`; cấp lại quyền sau khi đo. Chạy SAU T019/T020; nếu khi đó `tts_unavailable` vẫn còn thì ghi thời gian tới thông báo, đánh phần "câu nói đầu" của SC-003 là UNAVAILABLE (không phải đạt) — FR-006 · Verify: ≥ 4/5 lần ≤ 3 000 ms tới câu nói đầu (SC-003), log lưu ngoài repo
- [x] T012 [US2] Lặp T011 trên AVD hc-api36 — FR-006 · Verify: như T011
- [x] T013 [US2] Ghi kết quả vào docs/spikes/P1-S2-dung-an-toan.md §3 hạng mục 4 (xác nhận hoặc đề xuất điều chỉnh ADR-008 quyết định 1 cho Minh duyệt) — FR-006 · Verify: review
- [x] T014 [US2] Kiểm manifest release không có `USE_FULL_SCREEN_INTENT` và `ScenarioReceiver` — FR-011 · Verify: `apps/android/gradlew -p apps/android :app:processReleaseMainManifest` rồi grep manifest đã merge (hoặc bước CI tương ứng) không thấy hai mục này

---

## Phase 5: User Story 3 - Màn hình demo đọc được với người cao tuổi (Priority: P2)

**Goal**: tiêu đề demobank không chồng dòng; bộ ảnh qua `ux-elder-reviewer`

**Independent Test**: ảnh 200% màn chuyển tiền; báo cáo reviewer không còn High

- [x] T015 [US3] Chụp ảnh lỗi trước khi sửa: màn chuyển tiền demobank ở font_scale 2.0 trên hc-api36 — FR-007 · Verify: ảnh cho thấy tiêu đề chồng dòng (bằng chứng "đỏ trước")
- [x] T016 [US3] Sửa tiêu đề "Chuyển tiền đến tài khoản khác" trong apps/android/demobank/src/main/java/vn/hoicon/demobank/MainActivity.kt (line-height theo cỡ chữ, cho xuống dòng, không khóa cỡ chữ) — FR-007 · Verify: `apps/android/gradlew -p apps/android :demobank:lintDebug` + ảnh 200% không chồng dòng
- [x] T017 [US3] Bộ ảnh 100%/200% trên hc-api36 và hc-api34: demobank (đăng nhập, trang chủ, chuyển tiền, OTP mô phỏng, kết quả) + SafePause (lưu ngoài repo, ghi đường dẫn) — FR-008 · Verify: đủ 2 cỡ × 2 AVD × 6 màn
- [x] T018 [US3] Gửi bộ ảnh cho `ux-elder-reviewer`; sửa mục High thuộc demobank; mục thuộc E7 ghi sang P2-05 — FR-008 · Verify: báo cáo reviewer không còn High cho phạm vi spec này (SC-004)

---

## Phase 6: User Story 4 - Giọng nói trên máy ảo Linux (Priority: P3)

**Goal**: `tts_started` trên AVD Linux mà không đổi luật chọn giọng offline

**Independent Test**: kịch bản 10 lần, đếm `tts_started`

- [x] T019 [US4] Chẩn đoán `tts_unavailable` theo research R3 (engine mặc định, gói TTS, dữ liệu giọng vi-VN offline, ảnh hưởng `-no-audio`) — FR-009 · Verify: nguyên nhân ghi trong evidence.md kèm lệnh đã chạy
- [x] T020 [US4] Khắc phục ở **môi trường** (không sửa `Speaker.kt`, không sửa `scripts/emu-*.py|sh` — ngoài phạm vi làn A; nếu cần đổi script thì ghi đề xuất trong evidence.md) và ghi các bước (lệnh adb) vào docs/EMULATOR.md §1.2 — FR-009 · Verify: `emu-scenario.py --scenario fake_police --runs 10` ⇒ `tts_started` ≥ 9/10 trên hc-api36 và hc-api34 (SC-006); không khắc phục được ⇒ ghi giới hạn + `UNAVAILABLE`

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T021 Hồi quy sau mọi thay đổi: `emu-scenario.py --scenario fake_police --runs 10` trên hc-api36 và hc-api34; `:rules:test :app:lintDebug :demobank:lintDebug` — FR-010 · Verify: 10/10 mỗi AVD; build + lint xanh (SC-005)
- [x] T022 Reviewer: `/ponytail-review` cho thay đổi `:latency` + demobank + script; `security-privacy-reviewer` cho bộ đo (quyền shell, manifest debug/release) — FR-011 · Verify: không còn finding High

---

## Phase 8: Acceptance evidence *(bắt buộc)*

- [x] T023 Chạy `/speckit-converge` tới 0 finding hoặc chạm điều kiện dừng (docs/MASTER-PLAN.md §2.5; FTL thiếu tài khoản ⇒ BLOCKED trong evidence.md) — FR-001 · Verify: báo cáo converge
- [x] T024 Viết specs/001-safe-pause-real-device/evidence.md từ `.specify/templates/overrides/evidence-template.md` (SC-001…SC-006 có số + nguồn hoặc BLOCKED/UNAVAILABLE) — FR-004 · Verify: `python3 scripts/check-spec-trace.py`
- [x] T025 Cập nhật **dòng** P1-S1 và P1-S2 trong docs/ROADMAP.md (trạng thái + link `specs/001-safe-pause-real-device`; STATUS sửa sau merge) — FR-005 · Verify: `python3 scripts/check-spec-trace.py`

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 (T003–T004) → US1 (T005–T010). T007/T008 cần Firebase (W0-3); thiếu thì làm US2–US4 trước.
- T011/T012 (đo câu nói đầu) chạy sau T019/T020 (US4) để có `tts_started`; nếu US4 bị cắt thì phần giọng nói của SC-003 là UNAVAILABLE.
- US2 (T011–T014), US3 (T015–T018), US4 (T019–T020) độc lập với nhau và với phần FTL của US1; chạy tuần tự vì dùng
  chung một emulator (một emulator mỗi lúc — chạy lần lượt).
- T021–T022 sau mọi thay đổi code; T023–T025 cuối cùng.

### Thứ tự đề xuất khi chưa có Firebase
T001 → T002 → T003 → T004 → T005 → T006 → T015 → T016 → T017 → T018 → T019 → T020 → T011 → T012 → T013 → T014 →
T021 → T022 → (T007 → T008 → T009 → T010 khi có Firebase) → T023 → T024 → T025

## Implementation Strategy

- MVP = bộ đo có biến thể chạy trên AVD (T003–T006) + sửa demobank (T016) — làm ngay, không chờ tài khoản.
- Phần máy thật (T007–T010) là điều kiện gate G1 (08/11); hạn mềm 05/11, sau đó BLOCKED theo spec "Ngoài phạm vi".

## Notes

- Không đánh [x] khi Verify chưa chạy xanh; BLOCKED/UNAVAILABLE ghi lý do trong evidence.md.
- Ảnh và log thô để ngoài repo (không chứa dữ liệu cá nhân, nhưng nặng); evidence.md ghi đường dẫn.
- Commit chỉ khi Tiến/Minh yêu cầu.
