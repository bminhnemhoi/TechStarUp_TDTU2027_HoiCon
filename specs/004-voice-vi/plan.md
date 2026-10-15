# Implementation Plan: Giọng nói tiếng Việt trên máy (spike P1-S5 thu nhỏ)

**Branch**: `feat/004-voice-vi` (nối tiếp `feat/001-safe-pause-real-device`) | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-voice-vi/spec.md`

## Summary

Spike đo để quyết định, **không đổi app Lính gác**. Thêm module công cụ `:voicelab` (minSdk 33, debug) với các test
instrument chạy trên AVD:
1. Thăm dò giọng TTS vi-VN khi tắt mạng + đo `speak()` → `onStart` nguội/ấm.
2. Đo phát âm thanh thu sẵn (`MediaPlayer`) để so.
3. Tổng hợp WAV cho người nghe chấm.
4. Thăm dò + chạy `SpeechRecognizer` vi-VN từ **tệp** (không micro) trên 20 câu chuẩn × 2 bộ.

Phía máy tính: `scripts/voice-lab.sh` (đẩy tệp, chạy test, kéo log/WAV) + `scripts/voice-wer.py` (WER, ý định, bảng).
Kết quả + quyết định theo quy tắc đăng ký trước (FR-011) vào `docs/spikes/P1-S5-giong-noi.md`.

**Quyết định kỹ thuật cần Tiến duyệt trước `implement`** (sau đó chạy một mạch, §2.6):
- K1: module riêng `:voicelab` (không đụng `:app`, `:latency`).
- K2: `RECORD_AUDIO` chỉ ở `:voicelab` và chỉ khi R1 bắt buộc.
- K3: quy tắc quyết định FR-011 (ngưỡng p95 ấm ≤ 1 000 ms, điểm nghe ≥ 3,5, ý định ≥ 95%, WER ≤ 20%).
- K4: bản thu của đội + điểm người nghe ở ngoài repo, xóa sau 10/01/2027.

## Technical Context

**Language/Version**: Kotlin 2.4 (`:voicelab` minSdk 33, target/compileSdk 36) · Python 3.12 thư viện chuẩn (script)

**Primary Dependencies**: `android.speech.tts`, `android.speech.SpeechRecognizer`, `android.media.MediaPlayer`,
`androidx.test.runner`, `junit` — không thêm thư viện (Hiến chương VIII)

**Storage**: không DB. Bằng chứng thô ngoài repo `~/hoicon-evidence/004-voice-vi/{logs,audio,wav,ratings}`

**Testing**: `:voicelab:connectedDebugAndroidTest` trên hc-api36 + hc-api34 · `python3 -m unittest discover -s scripts/tests` ·
`apps/android/gradlew -p apps/android :rules:test :app:lintDebug :voicelab:lintDebug`

**Target Platform**: AVD hc-api36 (Android 16) + hc-api34 (Android 14), ảnh `google_apis_playstore`; máy thật nếu có (FTL)

**Project Type**: monorepo — chỉ làn A

**Performance Goals**: ngưỡng quyết định TTS p95 ấm ≤ 1 000 ms (đo, không phải tối ưu)

**Constraints**: mạng tắt khi đo TTS; không micro trực tiếp; không ghi âm cuộc gọi; một emulator một lúc (14 GB RAM);
không chạy Gradle song song với làn B

**Scale/Scope**: 20 câu × 2 bộ × 2 AVD; n ≥ 20 cho mỗi phép đo độ trễ

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Nguồn: `.specify/memory/constitution.md`.

| # | Nguyên tắc | Đụng tới? | Đạt / cách đảm bảo |
|---|---|---|---|
| I | Dừng an toàn offline ≤ 3 s, không chặn vĩnh viễn | Không (chỉ đo) | `:app` không đổi; FR-014 kiểm manifest + `:rules:test` |
| II | Riêng tư | **Có** (giọng người) | Bản thu ngoài repo, đồng ý bằng lời, xóa sau 10/01/2027; `:voicelab` không `INTERNET`; không micro trực tiếp; `security-privacy-reviewer` |
| III | LLM chỉ nâng | Không | — |
| IV | Công khai AI, đồng ý | Không có tin mới | Câu đọc thử là `pause_speech` có sẵn |
| V | Hợp đồng trước | Nhẹ | `data/voice/sentences.v1.json` có test cấu trúc; không API/DB |
| VI | UX người cao tuổi | Gián tiếp | Kết luận "nút bấm là chính" vào DESIGN-SYSTEM; không màn hình mới |
| VII | Bằng chứng trung thực | **Có** | Mọi số kèm AVD/máy thật + n; quy tắc quyết định đăng ký trước; thiếu ⇒ `BLOCKED` |
| VIII | Ít code | **Có** | Một module nhỏ, không thư viện; WER thư viện chuẩn; xóa được sau spike |
| IX | Chặn phát hành | Có | `:voicelab` không có buildType release, không vào AAB |

Kết quả: **ĐẠT**. Không vi phạm.

## Tái sử dụng *(mandatory)*

| Cần gì | Đã có ở đâu | Dùng lại / mở rộng / viết mới |
|---|---|---|
| Tiêu chí chọn giọng offline | `apps/android/app/.../pause/Speaker.kt::pickOfflineVietnamese` | **chép đúng tiêu chí** sang `:voicelab` (không phụ thuộc `:app`); test so khớp chuỗi tiêu chí trong review |
| Câu SafePause | `apps/android/app/src/main/res/values/strings.xml` `pause_speech` | **chép nguyên văn** (ghi nguồn + ngày) |
| Khung module đo + Gradle | `apps/android/latency/build.gradle.kts`, version catalog | **mẫu** cho `:voicelab/build.gradle.kts` (plugin application thay vì test) |
| Đo thời gian/log | `HcTiming`, `HcSpikeLog` (`:app`) | **mẫu** — `:voicelab` có logger `HC_VOICE` riêng, JSON một dòng |
| Chạy máy ảo, tắt/mở mạng, kéo log | `scripts/emu-start.sh`, `scripts/emu-scenario.py`, `scripts/android-env.sh`, `docs/EMULATOR.md` §1.2 (sửa gói giọng) | **dùng lại**; script mới `scripts/voice-lab.sh` gọi `adb` theo cùng quy ước |
| Test script Python | `scripts/tests/test_check_spec_trace.py` + CI `harness.yml` | **mở rộng**: thêm `test_voice_wer.py` (CI đã chạy `scripts/tests`; không sửa workflow — ngoài làn A, chỉ ghi đề xuất) |
| Ma trận thiết bị | `docs/spikes/device-matrix.md` | **mở rộng**: dòng giọng nói |

## Project Structure

### Documentation (this feature)

```text
specs/004-voice-vi/
├── spec.md · plan.md · research.md · quickstart.md · tasks.md
└── evidence.md           # phase cuối
```

### Source Code (repository root)

```text
apps/android/settings.gradle.kts                      # include(":voicelab")
apps/android/voicelab/build.gradle.kts                # application, minSdk 33, chỉ debug
apps/android/voicelab/src/main/AndroidManifest.xml    # không INTERNET; RECORD_AUDIO chỉ khi R1
apps/android/voicelab/src/main/res/raw/clip_pause_0.wav   # đoạn TỔNG HỢP (không giọng người) cho FR-004
apps/android/voicelab/src/main/kotlin/vn/hoicon/voicelab/{VoiceLog,PauseSpeech}.kt
apps/android/voicelab/src/androidTest/kotlin/vn/hoicon/voicelab/{TtsProbeTest,TtsLatencyTest,ClipLatencyTest,SynthesizeTest,SttProbeTest,SttRunTest}.kt
data/voice/sentences.v1.json
scripts/voice-lab.sh · scripts/voice-wer.py · scripts/tests/test_voice_wer.py
docs/spikes/P1-S5-giong-noi.md · docs/spikes/device-matrix.md · docs/DESIGN-SYSTEM.md · docs/EMULATOR.md · docs/ROADMAP.md (dòng P1-S5)
```

**Structure Decision**: module công cụ riêng, xóa được sau P2-05; không đụng `:app`, `:rules`, `:demobank`, `:latency`.

## Thiết kế & trade-off

- **Đo bằng test instrument** (giống `:latency`): chạy lặp lại được, kết quả JSON qua logcat, script kéo về. Không cần màn hình.
- **Nguội vs ấm (TTS)**: nguội = `TextToSpeech` mới mỗi lượt + `shutdown()` sau lượt (gần với lần đầu mở cửa sổ rủi ro);
  ấm = một engine, `speak` lặp lại cách nhau 1 s. Ghi cả thời gian `onInit`.
- **Tắt mạng**: `adb shell svc wifi disable && adb shell svc data disable` (script), kiểm lại bằng `dumpsys connectivity` trước khi đo.
- **STT từ tệp** (R3): đẩy WAV vào thư mục riêng của app (`adb push` → `/data/local/tmp` → test sao chép vào `filesDir`),
  mở `ParcelFileDescriptor` đọc PCM; mỗi câu một `SpeechRecognizer` mới; quá 15 s ⇒ ghi `timeout`.
- **Hai bộ câu**: *tổng hợp* = WAV do T-SynthesizeTest sinh từ 20 câu chuẩn (tất định, không cần người); *đội thu* = Tiến (và
  Minh nếu muốn) đọc 20 câu, `ffmpeg -ar 16000 -ac 1`. Bộ tổng hợp cho cận trên lạc quan; bộ đội thu mới dùng cho quyết định.
- **Ý định**: từ khóa đơn giản (`có|ừ|vâng|dạ có|phải` ⇒ yes; `không|chưa|đâu có` ⇒ no; `không biết|không rõ|chắc không` ⇒ unsure;
  "không biết" xét trước "không"). Ghi rõ đây là bộ phân loại của spike, sản phẩm làm lại ở P2-05 nếu STT được giữ.
- **Quy tắc quyết định FR-011** viết vào báo cáo **trước khi** chạy đo (commit thứ tự trong evidence: ngày ghi quy tắc ≤ ngày đo).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
