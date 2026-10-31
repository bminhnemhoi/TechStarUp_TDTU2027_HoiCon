# Research: Spec 001

## R1. Chọn biến thể E7 trong bộ đo
- **Decision**: tham số instrumentation `variant=view|compose` (mặc định `view`); trước mỗi lô, bộ đo chạy
  `run-as vn.hoicon.sentinel touch files/spike_compose_pause` (compose) hoặc `rm -f` (view) qua `executeShellCommand`.
- **Rationale**: `SafePauseActivity` đã đọc tệp cờ này ở bản debug; uid shell của UiAutomation được `run-as` với app
  debuggable ⇒ không đổi code sản phẩm.
- **Alternatives**: hai APK khác nhau (tốn lượt cài, dễ đo nhầm bản); Intent extra (phải sửa đường găng).
- **Kiểm**: log `safe pause ui=compose|views` (HcSpikeLog) phải khớp `variant` ở mọi lần đo; lệch ⇒ lần đó không hợp lệ.

## R2. Máy FTL
- **Decision**: Samsung dòng A chạy Android 14 + Pixel chạy Android 15 hoặc 16, chọn theo
  `gcloud firebase test android models list --filter="form=PHYSICAL"` lúc chạy.
- **Rationale**: spike S2 §6; Samsung A gần máy người cao tuổi, Pixel gần AOSP mới nhất.
- **Alternatives**: Xiaomi (rủi ro RB-6) — để khi có máy thật vật lý.

## R3. `tts_unavailable` trên AVD Linux
- **Giả thuyết** (kiểm theo thứ tự, dừng ở cái đúng):
  1. Google TTS trên ảnh hệ thống chưa tải dữ liệu giọng vi-VN offline (AVD Windows đã tải từ trước).
  2. Engine mặc định không phải `com.google.android.tts`.
  3. AVD chạy `-no-audio` làm engine báo lỗi khởi tạo.
- **Cách kiểm**: `adb shell settings get secure tts_default_synth`; `adb shell cmd package list packages | grep tts`;
  log `Speaker` khi khởi tạo; mở Cài đặt → Chuyển văn bản thành giọng nói → cài dữ liệu tiếng Việt (cần mạng một lần,
  sau đó offline).
- **Ràng buộc**: không đổi luật chọn giọng offline trong `Speaker.kt`.

## R4. Full-screen intent khi thu hồi SAW
- **Decision**: làm đúng §6(c) của spike S2 trên AVD 34 và 36, n ≥ 5 mỗi máy.
- **Kỳ vọng theo tài liệu** (ADR-008): máy mở khóa ⇒ heads-up, không mở activity ⇒ xác nhận quyết định 1.
