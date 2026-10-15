---

description: "Tasks — 004-voice-vi (spike P1-S5 thu nhỏ, làn A)"
---

# Tasks: Giọng nói tiếng Việt trên máy

**Input**: `specs/004-voice-vi/` (spec.md, plan.md, research.md, quickstart.md)

**Chế độ chạy**: **TỰ HÀNH MỘT MẠCH** (docs/MASTER-PLAN.md §2.6). Không có task "chờ duyệt". Thiếu thứ từ bên ngoài
(bản thu của đội, người nghe, máy thật) ⇒ ghi `BLOCKED: <lý do>` vào evidence.md, đánh dấu task `[x]` kèm chữ BLOCKED trong
dòng, làm tiếp. Chỉ dừng theo §2.5 (Verify đỏ 2 lần liên tiếp, analyze còn CRITICAL/HIGH) hoặc khi sắp vi phạm CLAUDE.md.

**Tests**: bắt buộc — script Python có `unittest` viết trước; bộ đo Android là test instrument.

**Môi trường**: một emulator một lúc; trước mỗi lần chạy máy ảo kiểm `free -g` (≥ 5 GB trống), không chạy Gradle khi làn B
đang chạy Gradle. Bằng chứng thô vào `~/hoicon-evidence/004-voice-vi/` (`$EV`).

## Format: `[ID] [P?] [Story] Description — FR-xxx · Verify: \`lệnh\``

---

## Phase 1: Setup

- [x] T001 Tra R1–R5 trong research.md (skill `documentation-lookup` hoặc developer.android.com), ghi kết luận + ngày tra + đường dẫn vào cột mới "Kết luận" của research.md; câu nào không rõ ⇒ dùng phương án mặc định, ghi rõ — FR-001, FR-007 · Verify: review
- [x] T002 Ghi **quy tắc quyết định FR-011** nguyên văn vào đầu `docs/spikes/P1-S5-giong-noi.md` (mục "Quy tắc đăng ký trước", ngày 15/10/2026) trước khi đo — FR-011, FR-012 · Verify: `git diff --stat docs/spikes/P1-S5-giong-noi.md`
- [x] T003 [P] Tạo `data/voice/sentences.v1.json`: 20 câu hư cấu (12 `answer` có `intent` yes/no/unsure, biến thể Bắc/Trung/Nam; 8 `story`), không chữ số dài, không tên thật — FR-008 · Verify: `python3 -m unittest scripts.tests.test_voice_wer -k sentences` (sau T004)

---

## Phase 2: Foundational

- [x] T004 [P] Viết TRƯỚC `scripts/tests/test_voice_wer.py`: chuẩn hóa (NFC, chữ thường, bỏ dấu câu, giữ dấu tiếng Việt), WER (giống hệt = 0; thiếu/thừa/thay từ), ý định ("không biết" ⇒ unsure trước "không" ⇒ no; "dạ có" ⇒ yes), kiểm cấu trúc `sentences.v1.json` (20 câu, 12 answer có intent, id duy nhất, không chuỗi ≥ 7 chữ số) — FR-008, FR-009 · Verify: `python3 -m unittest discover -s scripts/tests` (đỏ trước T005)
- [x] T005 Viết `scripts/voice-wer.py` (chỉ thư viện chuẩn): đọc `sentences.v1.json` + JSON kết quả nhận dạng, xuất bảng Markdown + JSON (WER từng câu/bộ, độ chính xác ý định, p50/p95 độ trễ) — FR-009 · Verify: `python3 -m unittest discover -s scripts/tests`
- [x] T006 Xác nhận CI sẵn có đã chạy test mới: `.github/workflows/harness.yml` (**không sửa** — ngoài làn A, §5) có `paths` `scripts/tests/**` + `specs/**` và bước `unittest discover -s scripts/tests`; ghi đề xuất "thêm `scripts/voice-*.py`, `data/voice/**` vào `paths`" vào evidence.md cho checkout chính — FR-009 · Verify: `grep -n "scripts/tests" .github/workflows/harness.yml && git diff --stat -- .github` (diff rỗng)
- [x] T007 Tạo module `:voicelab` (application `vn.hoicon.voicelab`, minSdk 33, chỉ debug, không `INTERNET`; `RECORD_AUDIO` chỉ khi T001 kết luận R1 bắt buộc) theo mẫu `apps/android/latency/build.gradle.kts`; `include(":voicelab")`; `VoiceLog` (JSON một dòng thẻ `HC_VOICE`), `PauseSpeech` (chép nguyên văn `pause_speech` + ghi nguồn) — FR-001, FR-014 · Verify: `apps/android/gradlew -p apps/android :voicelab:assembleDebug :voicelab:lintDebug`
- [x] T008 Viết `scripts/voice-lab.sh` (dùng `scripts/android-env.sh`): `--avd`, tắt/mở mạng + kiểm `dumpsys connectivity`, cài `:voicelab`, `pm grant` khi cần, chạy một lớp test, kéo log `HC_VOICE` + WAV về `$EV`, chuyển WAV synth sang 16 kHz mono s16 bằng `ffmpeg` (`$EV/wav16/`); cảnh báo "chỉ chạy trên AVD/máy thử" — FR-002, FR-005, FR-007 · Verify: `bash -n scripts/voice-lab.sh` (shellcheck chưa cài ⇒ ghi UNAVAILABLE vào evidence)

**Checkpoint**: script + module dựng được, test Python xanh.

---

## Phase 3: User Story 1 — TTS offline + độ trễ (P1) 🎯

**Independent Test**: `scripts/voice-lab.sh --avd hc-api36 --probe tts` rồi `--avd hc-api34` ⇒ bảng giọng + p50/p95.

- [x] T009 [US1] `TtsProbeTest`: liệt kê giọng `vi` (tên, cần mạng, quality, latency, not-installed, engine mặc định), chọn giọng theo **đúng** tiêu chí `Speaker.pickOfflineVietnamese`, phân biệt "không có giọng" vs "giọng hỏng" (`speak` không `onStart` trong 5 s) — FR-002 · Verify: chạy trên hc-api36 + hc-api34 mạng tắt, log `HC_VOICE probe=tts` có trong `$EV/logs/`
- [x] T010 [US1] `TtsLatencyTest`: câu đầu `PauseSpeech`, nguội (engine mới mỗi lượt) + ấm (một engine, cách 1 s), n = 20 mỗi kiểu; ghi `onInit` và `speak→onStart` — FR-003 · Verify: 2 AVD × 2 kiểu đủ 20 giá trị trong log (SC-002)
- [x] T011 [US1] `ClipLatencyTest` + `res/raw/clip_pause_0.wav` (tổng hợp, ≤ 200 KB, ghi nguồn sinh): `MediaPlayer` nguội/ấm, n = 20, đo tới khung đầu (R4) — FR-004 · Verify: 2 AVD × 2 kiểu đủ 20 giá trị (SC-003)
- [x] T012 [US1] `SynthesizeTest`: `synthesizeToFile` 4 câu `pause_speech` + 4 cụm khó + 20 câu chuẩn ⇒ WAV tần số gốc (cho người nghe) + bản 16 kHz mono do `voice-lab.sh` chuyển (cho bộ STT tổng hợp); kéo về `$EV/wav/`, `$EV/wav16/` — FR-005 · Verify: `ls $EV/wav/*.wav | wc -l` ≥ 28 và `ffprobe` một tệp `wav16` báo 16000 Hz, 1 kênh

**Checkpoint**: SC-001…SC-003 có số trên 2 AVD.

---

## Phase 4: User Story 2 — Nhận dạng vi-VN (P2)

**Independent Test**: `scripts/voice-lab.sh --avd hc-api36 --probe stt --set synthetic` ⇒ JSON nhận dạng ⇒ `voice-wer.py`.

- [x] T013 [US2] `SttProbeTest`: `isOnDeviceRecognitionAvailable`, `checkRecognitionSupport` vi-VN, thử `triggerModelDownload` một lần (chờ ≤ 120 s), ghi kết quả — FR-006 · Verify: log `HC_VOICE probe=stt` trên 2 AVD
- [x] T014 [US2] `SttRunTest`: đọc danh sách WAV đã đẩy, mỗi câu một bộ nhận dạng (ưu tiên trên máy; bộ mặc định chỉ khi trên máy không có, gắn `recognizer=default_network`), `EXTRA_AUDIO_SOURCE` + 3 extra định dạng (R3), quá 15 s ⇒ `timeout`; không mở micro — FR-007 · Verify: bộ tổng hợp (T012) 20/20 câu có kết quả hoặc mã lỗi trên 2 AVD
- [x] T015 BLOCKED: chờ Tiến thu âm (data/voice/sentences.v1.json) — [US2] Chạy `SttRunTest` với **bộ đội thu** (`$EV/audio/team/*.wav`, chuyển định dạng theo quickstart). Chưa có bản thu ⇒ `BLOCKED: chưa có bản thu của đội` trong evidence, làm tiếp — FR-007, FR-010 · Verify: JSON kết quả hoặc dòng BLOCKED
- [x] T016 [US2] `python3 scripts/voice-wer.py` cho mọi bộ × AVD có kết quả ⇒ `$EV/wer-*.md|json` — FR-009 · Verify: bảng có WER + độ chính xác ý định + p50/p95 (SC-004)

**Checkpoint**: SC-004 có số (hoặc BLOCKED có lý do).

---

## Phase 5: User Story 3 — Quyết định + tài liệu (P3)

- [x] T017 BLOCKED: chờ người nghe chấm điểm MOS — [US3] Người nghe chấm WAV của T012 (1–5 độ rõ + dễ chịu, ≥ 3 người ≥ 18, ≥ 1 người ≥ 60 nếu có, ghi "người nghe k (nhóm tuổi)", đồng ý bằng lời) ⇒ `$EV/ratings.md`; thiếu ⇒ ghi số người thực có hoặc BLOCKED — FR-010, FR-011 · Verify: bảng điểm có n người (SC-005)
- [x] T018 [US3] Viết `docs/spikes/P1-S5-giong-noi.md`: bảng giọng, độ trễ TTS vs clip, WER/ý định, điểm nghe, **quyết định theo quy tắc T002**, rủi ro còn lại, đề xuất nguồn âm thanh thu sẵn cho P2-05 (không mua) — FR-011, FR-012 · Verify: review (mọi số có môi trường + n)
- [x] T019 [P] [US3] `docs/DESIGN-SYSTEM.md`: thêm nguyên tắc "nút bấm là chính, giọng nói chỉ bổ trợ" (kèm link báo cáo); `docs/spikes/device-matrix.md`: dòng giọng nói; `docs/EMULATOR.md`: cách chạy `voice-lab.sh` — FR-012 · Verify: review
- [x] T020 BLOCKED: chờ Firebase/máy thật (W0-3) — [US3] Máy thật: có FTL/máy mượn ⇒ chạy T009, T010, T013 trên ≥ 1 máy; không có ⇒ `BLOCKED: chưa có Firebase/máy thật (W0-3)` — FR-013 · Verify: số đo hoặc dòng BLOCKED

---

## Phase 6: Polish & Cross-Cutting

- [x] T021 Kiểm `:app` không đổi: `:app:processReleaseMainManifest` + grep manifest đã merge (0 `RECORD_AUDIO`, 0 `INTERNET`); manifest `:voicelab` 0 `INTERNET`; `git ls-files '*.wav' '*.m4a' '*.mp3'` chỉ còn `clip_pause_0.wav` tổng hợp — FR-010, FR-014 · Verify: lệnh grep + ls-files dán vào evidence (SC-006)
- [x] T022 Reviewer: `security-privacy-reviewer` (quyền micro, dữ liệu giọng, script adb), `/ponytail-review` — Verify: không còn finding High
- [x] T023 Chạy lại quickstart.md từ đầu trên hc-api36 — Verify: các bước chạy được

---

## Phase 7: Acceptance evidence *(bắt buộc)*

- [x] T024 `/speckit-converge` tới 0 finding hoặc chạm §2.5 (finding bị chặn ⇒ BLOCKED) — Verify: báo cáo converge
- [x] T025 Cổng các tầng: `apps/android/gradlew -p apps/android :rules:test :app:testDebugUnitTest :app:lintDebug :voicelab:lintDebug :voicelab:assembleDebug` · `python3 -m unittest discover -s scripts/tests` · `python3 scripts/check-spec-trace.py` — Verify: output dán vào evidence.md
- [x] T026 Viết `specs/004-voice-vi/evidence.md` theo `.specify/templates/overrides/evidence-template.md` (SC-001…006 có số + môi trường + n hoặc BLOCKED) — Verify: `python3 scripts/check-spec-trace.py`
- [x] T027 Cập nhật **dòng P1-S5** trong `docs/ROADMAP.md` (trạng thái + link spec + báo cáo; không sửa khối STATUS) — Verify: `python3 scripts/check-spec-trace.py`

---

## Dependencies & Execution Order

- T001 → T007 (quyền micro) · T002 trước mọi phép đo (T009+) · T003 + T004 → T005 · T007 + T008 → Phase 3–5.
- Trong Phase 3: T009 → T010 → T011 → T012 (cùng một phiên máy ảo, đổi AVD giữa chừng: chạy hết hc-api36 rồi hc-api34).
- T012 → T014 (bộ tổng hợp) · T014 → T015 → T016 · T016 + T017 → T018.
- T015, T017, T020 có thể BLOCKED mà không chặn T018 (báo cáo ghi rõ phần thiếu).

## Notes

- Không đánh `[x]` khi Verify chưa chạy; bước không chạy được ghi SKIPPED/UNAVAILABLE/BLOCKED kèm lý do trong evidence.md.
- Không đọc `.env`, keystore. Không đẩy bản thu giọng người vào repo, log ứng dụng hay dịch vụ ngoài.
- Commit chỉ khi Tiến yêu cầu.

---

## Phase 8: Convergence

- [x] T028 Sửa `specs/004-voice-vi/quickstart.md` cho chạy được từng chữ: `voice-wer.py --results` dùng `stt-synthetic-*.jsonl`/`stt-team-*.jsonl` (không dùng glob khớp log thăm dò), nêu `--allow-network` và `--confirm-team-audio-to-cloud`, `--set` đi kèm — per T023 (partial) · Verify: chạy đúng các lệnh `voice-wer.py` trong quickstart sau khi sửa, thấy bảng WER
- [x] T029 `scripts/voice-lab.sh`: sau khi tắt mạng, in thêm dòng `dumpsys connectivity` (mạng mặc định) cùng kết quả `ping` — per plan: "kiểm lại bằng dumpsys connectivity" (partial) · Verify: `bash -n scripts/voice-lab.sh` + dòng `dumpsys` xuất hiện khi chạy trên máy ảo
