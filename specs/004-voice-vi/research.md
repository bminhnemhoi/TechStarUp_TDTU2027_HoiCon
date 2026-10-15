# Research: 004-voice-vi

Câu hỏi mở cần trả lời **ở T001** (đọc tài liệu Android chính thức qua skill `documentation-lookup`/Context7 hoặc
developer.android.com; ghi ngày tra + đường dẫn). Không câu nào là điểm dừng: mỗi câu có phương án mặc định.

| # | Câu hỏi | Phương án mặc định nếu tài liệu không rõ | Ảnh hưởng | Kết luận (T001, 15/10/2026) |
|---|---|---|---|---|
| R1 | Bộ nhận dạng có đòi app gọi giữ `RECORD_AUDIO` khi âm thanh đến từ `EXTRA_AUDIO_SOURCE` (tệp) không? | Khai `RECORD_AUDIO` **chỉ ở `:voicelab`**, cấp bằng `pm grant` trong script; `:app` không đổi | FR-001, FR-014 | **Dùng mặc định.** Javadoc `SpeechRecognizer`: "the application must have RECORD_AUDIO permission to use this class"; `EXTRA_AUDIO_SOURCE` không miễn quyền này. ⇒ khai `RECORD_AUDIO` **chỉ ở `:voicelab`**, `pm grant` trong script; sẽ kiểm bằng thực nghiệm ở T013/T014 (nếu chạy được khi chưa cấp quyền thì ghi lại và bỏ quyền). |
| R2 | Ảnh `google_apis_playstore` API 34/36 có bộ nhận dạng **trên máy** cho vi-VN không; `triggerModelDownload` có cần đăng nhập/mạng không? | Thăm dò thật (FR-006). Không có ⇒ đo bộ mặc định với nhãn "mạng — không dùng cho sản phẩm", hoặc `BLOCKED` nếu bộ mặc định cũng không chạy | SC-004, FR-011 | **Chưa biết từ tài liệu** — `isOnDeviceRecognitionAvailable` chỉ báo có dịch vụ nhận dạng trên máy; `triggerModelDownload` "might trigger user interaction to approve the download". ⇒ thăm dò thật ở T013 (mặc định giữ nguyên). |
| R3 | Định dạng tệp mà `EXTRA_AUDIO_SOURCE` nhận: PCM 16-bit thô hay WAV có header; cần `EXTRA_AUDIO_SOURCE_ENCODING/SAMPLING_RATE/CHANNEL_COUNT`? | PCM 16-bit LE, 16 kHz, mono, **bỏ header WAV** (đọc 44 byte đầu), khai đủ 3 extra | FR-007 | **Khác mặc định một chút:** `EXTRA_AUDIO_SOURCE` là `ParcelFileDescriptor` đã mở tới nguồn âm thanh; mặc định encoding = `ENCODING_PCM_16BIT`, kênh = 1, tần số = 16000; "the caller is responsible for closing the audio". Không nhắc header WAV ⇒ đưa **PCM thô** (bỏ 44 byte header), vẫn khai đủ 3 extra. Nguồn FD: `ParcelFileDescriptor.createPipe()` + luồng ghi PCM (hoặc FD tệp đã tìm tới sau header). |
| R4 | Cách đo "khung âm thanh đầu tiên" của `MediaPlayer` đáng tin nhất | `AudioTrack`/`MediaPlayer.getTimestamp()` hỏi vòng 5 ms tới khi `framePosition > 0`; dự phòng `currentPosition > 0` (ghi rõ độ phân giải) | FR-004 | **Dùng mặc định.** `MediaPlayer` không có mã `INFO` cho "bắt đầu render âm thanh" (chỉ `VIDEO_RENDERING_START`) ⇒ hỏi `getTimestamp()`/`AudioTrack` vòng 5 ms; dự phòng `currentPosition > 0`, ghi độ phân giải. (Phần suy luận từ API đã biết, kiểm khi biên dịch/chạy T011.) |
| R5 | `onStart` của `UtteranceProgressListener` có khớp lúc ra loa không (độ lệch đã biết)? | Dùng `onStart` như 001 (`tts_started`) để so được với số SafePause; ghi giới hạn trong báo cáo | FR-003 | **Xác nhận, có giới hạn.** Javadoc `onStart`: "called when an utterance 'starts' as perceived by the caller. This will be soon before audio is played back" ⇒ gần với lúc ra loa nhưng **không phải** mốc ra loa; dùng cùng mốc với `tts_started` của 001 để so được, ghi giới hạn vào báo cáo. |

## Đã chốt (không cần tra thêm)

- **Module riêng `:voicelab`** (application + `androidTest`, chạy bằng `connectedDebugAndroidTest`) thay vì thêm vào `:latency`:
  `:latency` tự-instrument nhằm vào `:app` (`targetProjectPath`) ⇒ thêm quyền micro ở đó sẽ trộn vào quy trình đo SafePause.
  Module riêng giữ `:app` sạch quyền và dễ xóa sau spike.
- **Không thêm thư viện**: chỉ `android.speech.*`, `android.media.*`, `androidx.test.runner`, `junit` (đã có trong version catalog).
- **WER bằng Python thư viện chuẩn** (`unicodedata`, `re`, `json`): không cần `jiwer`.
- **Âm thanh "thu sẵn" để đo độ trễ** = WAV tổng hợp bằng chính TTS lúc build bộ đo (hoặc commit một tệp tổng hợp ≤ 200 KB):
  đo cơ chế phát, không đo chất lượng giọng người. Chất lượng giọng người để P2-05.

**Nguồn tra T001:** AOSP `frameworks/base/core/java/android/speech/{RecognizerIntent,SpeechRecognizer}.java`, `tts/UtteranceProgressListener.java` (nhánh `main`, tra 15/10/2026 — trang developer.android.com quá dài, WebFetch cắt cụt nên đọc javadoc nguồn).
