# Bằng chứng nghiệm thu: Giọng nói tiếng Việt trên máy (spike P1-S5 thu nhỏ)

**Spec**: `specs/004-voice-vi/spec.md` · **Mã ROADMAP**: P1-S5 · **Nhánh/PR**: `feat/004-voice-vi` (chưa commit, chưa PR — theo lệnh) · **Ngày**: 15/10/2026

<!-- Mọi số đo là MÁY ẢO (hc-api36 Android 16, hc-api34 Android 14; Linux headless -no-audio), không phải máy thật. Bằng chứng thô ngoài repo:
     ~/hoicon-evidence/004-voice-vi/{logs,wav,wav16,wer*,…} (quyền 700). Tên tệp log ghi trong docs/spikes/P1-S5-giong-noi.md §10. -->

**Trình tự quy tắc → đo (T002 trước T009+):** `spec.md` sửa lần cuối 15:10; quy tắc đăng ký trước viết vào đầu `docs/spikes/P1-S5-giong-noi.md` §0 lúc **15:11:38**;
phép đo đầu tiên (`tts-hc-api36-20261015-151755`) chạy lúc **15:17:55**. Chỉ chứng minh bằng giờ sửa tệp (không commit theo lệnh).

## Tiêu chí thành công (SC) ↔ số đo

| SC | Ngưỡng | Đo được | Môi trường (máy ảo / FTL / máy thật, n) | Đạt? | Bằng chứng |
|---|---|---|---|---|---|
| SC-001 | bảng giọng vi-VN khi tắt mạng, cả 2 AVD | hc-api36 và hc-api34: 11 giọng `vi`, 6 offline + 5 cần mạng; chọn `vi-VN-language`; thử nói `ok` | máy ảo hc-api36 + hc-api34, mạng tắt (ping 8.8.8.8 thất bại, `Active default network: none`), n = 1 lần thăm dò/AVD | **Đạt** | `logs/tts-hc-api36-20261015-160107.jsonl`, `logs/tts-hc-api34-20261015-153911.jsonl`; báo cáo §1 |
| SC-002 | `speak→onStart` p50/p95 nguội và ấm; ngưỡng quyết định p95 ấm ≤ 1 000 ms | api36: nguội 59/**64** ms (+`onInit` p95 370), ấm 1/**3** ms · api34: nguội 355/**404** ms (+`onInit` p95 411), ấm 1/**1** ms | máy ảo hc-api36 + hc-api34, mạng tắt, n = 20 mỗi kiểu mỗi AVD | **Đạt** (p95 ấm 3 / 1 ms ≤ 1 000) — số ấm lạc quan (cùng một câu, có thể do bộ nhớ đệm) | như SC-001; báo cáo §2 (kèm dao động giữa lượt) |
| SC-003 | độ trễ phát clip thu sẵn p50/p95 nguội/ấm để so với SC-002 | api36: nguội pos 40/**42**, ấm 33/**35** ms · api34: nguội 40/**50**, ấm 34/**36** ms (lượt sớm api36: 59/69 và 34/38) | máy ảo hc-api36 + hc-api34, mạng tắt, n = 20 mỗi kiểu mỗi AVD, clip tổng hợp 24 kHz | **Đạt** | `logs/clip-hc-api36-20261015-160244.jsonl`, `logs/clip-hc-api34-20261015-154103.jsonl`; báo cáo §2 |
| SC-004 | WER + độ chính xác ý định cho bộ tổng hợp và bộ đội thu, mỗi AVD có bộ nhận dạng, ghi "trên máy"/"mạng" | **Bộ tổng hợp:** api36 trên máy WER 7,2 %, ý định 12/12 · api34 mạng WER 8,6 %, ý định 11/12 (api34 không có vi-VN trên máy). **Bộ đội thu: BLOCKED: chờ Tiến thu âm (data/voice/sentences.v1.json)** | máy ảo hc-api36 + hc-api34, n = 20 câu (bộ tổng hợp, TTS hc-api36 đọc lại); bộ đội thu n = 0 | **Một phần**: bộ tổng hợp đạt, bộ đội thu BLOCKED | `wer-final36/wer.md`, `wer/wer.md` (+ nhãn `on_device`/`default_network`); báo cáo §3 |
| SC-005 | điểm nghe TB (1–5) ≥ 3 người, ≥ 1 người ≥ 60 tuổi nếu có | **BLOCKED: chờ người nghe chấm điểm MOS** — 0 người nghe; 28 WAV sẵn ở `wav/` | WAV tổng hợp hc-api36, nghe qua loa điện thoại; n = 0 người | **BLOCKED** (đường chính TTS "chưa chốt" theo §0) | `wav/*.wav` (28 tệp, ngoài repo); báo cáo §4 |
| SC-006 | quyết định TTS + STT khớp 100 % quy tắc FR-011; `:app` release 0 `RECORD_AUDIO`/0 `INTERNET`; repo 0 tệp giọng người thật | TTS: điều kiện 1–2 đạt, điều kiện 3 thiếu dữ liệu ⇒ đường chính "chưa chốt"; STT: thiếu bản thu ⇒ "MVP chỉ nút bấm". `:app` release: `RECORD_AUDIO`=0, `INTERNET`=0; `git ls-files --cached --others --exclude-standard` âm thanh: chỉ `clip_pause_0.wav` (tổng hợp) | máy ảo (số đo) + manifest đã merge `:app:processReleaseMainManifest`, 15/10/2026, n = 1 | **Đạt** (reviewer đối chiếu §0↔§6: không diễn giải lại) | báo cáo §6; lệnh ở "Cổng các tầng" |

## Yêu cầu chức năng (FR) ↔ test

| FR | Test / cách kiểm | Kết quả |
|---|---|---|
| FR-001 | `:voicelab:assembleDebug :voicelab:lintDebug`; manifest đã merge của `:voicelab` chỉ có `RECORD_AUDIO` (R1 thực nghiệm: thiếu ⇒ lỗi 9 ở bộ mặc định api34), 0 `INTERNET`; không buildType release (`beforeVariants`); `:app` không phụ thuộc `:voicelab` | Đạt |
| FR-002 | `TtsProbeTest` trên 2 AVD | Đạt (bảng giọng; phân biệt `no_voice`/`broken_voice` có mã nhưng **chưa gặp ca giọng hỏng** nên nhánh `broken_voice` chưa được thử) |
| FR-003 | `TtsLatencyTest` n = 20 × (nguội, ấm) × 2 AVD | Đạt |
| FR-004 | `ClipLatencyTest` n = 20 × (nguội, ấm) × 2 AVD; clip 112 KB ≤ 200 KB, tổng hợp | Đạt |
| FR-005 | `SynthesizeTest` + `voice-lab.sh --probe synth`: 28 WAV gốc + 28 WAV 16 kHz mono (`ffprobe` = 16000 Hz, 1 kênh) | Đạt |
| FR-006 | `SttProbeTest` trên 2 AVD (kể cả `triggerModelDownload` 1 lần, chờ 120 s, có và không có mạng) | Đạt |
| FR-007 | `SttRunTest` trên 2 AVD, không mở micro. **Lệch có chủ đích so với chữ của spec:** âm thanh đưa qua `ParcelFileDescriptor.createPipe()` (đọc từ tệp, ghi đúng nhịp 100 ms/khối) thay vì descriptor tệp, vì descriptor tệp cho kết quả rỗng; bản chép lấy từ kết quả từng phần khi kết quả cuối rỗng (`transcript_source`) | Đạt (đề xuất cập nhật chữ FR-007 — mục "Còn tồn") |
| FR-008 | `test_voice_wer.SentencesTest` (20 câu, 12 `answer`, id duy nhất, không chữ số, phân loại ý định khớp nhãn) | Đạt |
| FR-009 | `test_voice_wer.py` (chuẩn hóa NFC, WER, ý định, percentile, CLI, JSONL) + `test_voice_lab_args.py`; `ruff` sạch | Đạt (31 test) |
| FR-010 | Bản thu/điểm ngoài repo (`~/hoicon-evidence/004-voice-vi/`, quyền 700); `.gitignore` chặn âm thanh ở `apps/android/voicelab/`, `data/voice/`; transcript không vào logcat (0/4 480 dòng chứa câu chuẩn); reviewer kiểm | Đạt |
| FR-011 | Quy tắc §0 ghi trước mọi phép đo; quyết định §6 khớp, kèm điều khoản "thiếu dữ liệu" đăng ký trước | Đạt |
| FR-012 | `docs/spikes/P1-S5-giong-noi.md` (bảng giọng, độ trễ, WER/ý định, điểm nghe BLOCKED, quyết định, rủi ro, nguồn âm thanh); `docs/DESIGN-SYSTEM.md` "nút bấm là chính"; dòng P1-S5 ROADMAP | Đạt |
| FR-013 | **BLOCKED: chờ Firebase/máy thật (W0-3)** — chưa chạy trên máy thật | BLOCKED |
| FR-014 | `:app:processReleaseMainManifest` (0 `RECORD_AUDIO`, 0 `INTERNET`); `:rules:test` 54/54; `:app:lintDebug` xanh; `git diff` của `app`/`rules`/`latency`/`demobank` rỗng | Đạt |

## Cổng các tầng (lệnh đã chạy)

| Tầng | Lệnh | Kết quả |
|---|---|---|
| Backend | — | Không áp dụng (không đụng `backend/`) |
| Android | `apps/android/gradlew -p apps/android --no-build-cache :rules:cleanTest :rules:test :app:cleanTestDebugUnitTest :app:testDebugUnitTest :voicelab:cleanTestDebugUnitTest :voicelab:testDebugUnitTest :app:lintDebug :voicelab:lintDebug :voicelab:assembleDebug :voicelab:assembleDebugAndroidTest :app:processReleaseMainManifest` | **BUILD SUCCESSFUL**; `:rules` 54 test, 0 lỗi; `:voicelab` JVM 2 test, 0 lỗi; `:app:testDebugUnitTest` không có test nguồn (NO-SOURCE) |
| Python | `python3 -m unittest discover -s scripts/tests` · `uvx ruff check scripts/voice-wer.py scripts/tests` | 31 test OK · ruff sạch |
| Web | — | Không áp dụng |
| Hook | — | Không áp dụng (không đụng `.claude/hooks`) |
| Máy ảo | `bash scripts/voice-lab.sh --avd hc-api36\|hc-api34 --probe tts\|clip\|synth\|stt [--set synthetic] [--allow-network]` (quickstart chạy lại đầy đủ trên hc-api36 ở T023) | Đạt, xem SC. `emu-scenario.py` **không chạy**: không đổi code cảm biến Android (`:app` không đổi) |
| Eval | — | Không áp dụng (không đổi agent/prompt) |
| Truy vết | `python3 scripts/check-spec-trace.py` | `check-spec-trace: 2 spec, 0 lỗi` (29/29 task đã tick, trong đó T015/T017/T020 ghi BLOCKED) |
| Quyền riêng tư | skill `privacy-audit` | **SKIPPED**: bắt buộc từ M1, chưa chạy ở spec này; thay bằng `security-privacy-reviewer` (bên dưới) |

## Review

| Reviewer | Kết quả | Đã xử lý |
|---|---|---|
| `security-privacy-reviewer` | 0 Critical · 2 High · 4 Medium · 4 Low. High: (H1) `--set team --allow-network` đưa giọng người thật tới bộ nhận dạng mạng không có cổng chặn; (H2) máy thử không có `-no-audio` và `RECORD_AUDIO` luôn được cấp ⇒ nếu bộ nhận dạng của hãng bỏ qua nguồn tệp thì mở micro. Medium: kiểm `-no-audio` không gắn đúng AVD; dọn dẹp bản sao thật không bảo đảm; thư mục bằng chứng quyền 777; `.gitignore` không chặn âm thanh | Đã sửa hết (báo cáo §11): cờ `--confirm-team-audio-to-cloud` + chặn trong `SttRunTest`; `RECORD_AUDIO` mặc định thu hồi (chỉ cấp cho bộ mặc định); team trên máy thật cần `HC_VOICE_ALLOW_TEAM_ON_DEVICE=1`; kiểm `-no-audio` theo đúng tiến trình AVD; trap dọn dẹp mọi đường thoát; `umask 077` + `chmod 700`; `.gitignore` trong module/`data/voice`. Low: khôi phục đúng trạng thái mạng ban đầu, vòng `read`, chỉnh câu DESIGN-SYSTEM, ghi chú §0 siết chặt hơn FR-011, bảng lượt chạy chính thức (§10). **Chưa chạy lại reviewer sau khi sửa** — các sửa được kiểm bằng thực nghiệm (từ chối team+mạng rc=2, dọn dẹp xác nhận bằng `run-as ls`/`ls /data/local/tmp`, wifi=1 sau khi chạy, STT quyền thu hồi vẫn 20/20 trên api36) |
| `ux-elder-reviewer` | Không áp dụng: không có màn hình/câu chữ mới cho người cao tuổi | — |
| `/ponytail-review` | Tự rà theo skill (không tạo subagent riêng): `--avd` chưa lọc vào tên tệp; `fail(...) as Nothing`; đếm lỗi bằng chuỗi `"error":null`; thông báo `'sentence_id'` khó hiểu | Đã sửa cả 4 (+ test `test_voice_lab_args.py`); không còn mã thừa đáng xóa: `Wav.kt`, `SttSupport`, `PauseSpeechSourceTest` đều được dùng |

## `/speckit-converge`

2 vòng. Vòng 1: 2 finding (F1 MEDIUM quickstart chạy nguyên văn sẽ lỗi; F2 LOW kiểm offline thiếu `dumpsys connectivity`) ⇒ T028, T029 (Phase 8) đã làm và kiểm. Vòng 2: **0 finding**
(không tạo thêm task). Lệch có chủ đích FR-007 không phải gap (ghi ở FR-007 và "Còn tồn").

## Còn tồn / hoãn có chủ đích

- **BLOCKED (ngoài tầm, spec chưa được ☑; ROADMAP P1-S5 giữ ◐):**
  - T015 / SC-004 bộ đội thu — **BLOCKED: chờ Tiến thu âm (data/voice/sentences.v1.json)**. Chạy lại: thu 20 câu → `$EV/audio/team/<id>.wav` (quickstart) → `voice-lab.sh --probe stt --set team` rồi `voice-wer.py`.
  - T017 / SC-005 điểm nghe — **BLOCKED: chờ người nghe chấm điểm MOS** (≥ 3 người, 28 WAV ở `wav/`).
  - T020 / FR-013 máy thật — **BLOCKED: chờ Firebase/máy thật (W0-3)**; cần cho G1 (08/11).
- **Đề xuất cho checkout chính (ngoài làn A, không tự sửa):** (1) cập nhật chữ `spec.md` FR-007 ("đường ống đọc từ tệp"; bản chép từ kết quả từng phần); (2) `.gitignore` gốc chặn `*.wav|*.m4a|*.mp3` và hook `guard-privacy` kiểm âm thanh; (3) thêm `scripts/voice-*.py`, `data/voice/**` vào `paths` của `.github/workflows/harness.yml` (T006: hiện `scripts/tests/**` + `specs/**` đã kích hoạt `unittest` nên chưa chặn); (4) câu "âm thanh có thể được gửi tới Google" vào mẫu đồng ý bằng lời cho người thu (skill `consent-copy`); (5) **ADR-007/008:** ghi số nguội + khởi tạo (370 / 411 ms, máy ảo) và rằng `onStart` ≠ ra tiếng — chờ số máy thật; **không sửa ADR**.
- **Rủi ro kỹ thuật cần theo dõi (báo cáo §7):** chọn giọng bị hòa điểm (nên chọn theo tên sau khi nghe); bộ nhận dạng trên máy chỉ có vi-VN ở API 36 (không ở API 34) và trả chữ qua kết quả từng phần; máy ảo không đo đường ra loa.
- **Thứ tự thực hiện lệch tasks.md một chỗ:** T012 chạy trước T011 vì clip mẫu sinh từ TTS (ghi ở báo cáo §2).
