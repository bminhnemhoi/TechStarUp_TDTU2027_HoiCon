# Môi trường máy ảo Android cho HỏiCon

> Minh chưa có điện thoại Android ⇒ phát triển và kiểm thử trên máy ảo (AVD). File này ghi cách dựng lại môi trường,
> kịch bản mô phỏng và **giới hạn** của máy ảo. Quy trình kiểm thử từng bước: skill `android-emulator-test`.

## 1. Toolchain (tất cả trên D:, ổ C: gần đầy)

| Thành phần | Vị trí | Ghi chú |
|---|---|---|
| JDK 21 (Temurin) | `D:\Android\jdk-21` | Gradle/AGP dùng qua `org.gradle.java.home` trong `D:\.gradle\gradle.properties`; `JAVA_HOME` toàn máy vẫn là JDK 25 |
| Android SDK | `D:\Android\Sdk` (~4 GB) | platform-tools, emulator, `platforms;android-36`, `build-tools;36.1.0` (+ `36.0.0` do AGP 9.4.1 tự cài khi build lần đầu), system image API 36/34/29 `google_apis_playstore;x86_64` |
| Android CLI | `D:\Android\Sdk\cmdline-tools\latest\bin\android.exe` | thay `sdkmanager` (đã ngừng phát triển): `sdk install`, `layout`, `screen capture`, `docs` |
| AVD | `D:\Android\avd` | `ANDROID_AVD_HOME` |
| Gradle cache | `D:\.gradle` | `GRADLE_USER_HOME` |
| Tăng tốc | WHPX (Windows Hypervisor Platform) | `emulator -accel-check` ⇒ "WHPX … is installed and usable"; chạy chung được với Docker/WSL2 |

**Dựng lại từ đầu** (Git Bash, thư mục repo):
```bash
bash scripts/setup-android.sh          # JDK 21 + cmdline-tools + gói SDK (idempotent, log: D:/Android/setup*.log)
powershell -ExecutionPolicy Bypass -File scripts/env-android.ps1   # biến môi trường người dùng + PATH + JDK cho Gradle
bash scripts/avd-create.sh             # 3 AVD (idempotent; --recreate để tạo lại)
```

**Bẫy đã gặp:**
- `sdkmanager.bat` / `avdmanager.bat` chạy qua cmd.exe ⇒ tham số `"system-images;android-36;…"` bị tách tại `;`.
  Cách xử lý: `android.exe sdk install "<gói>"` và gọi thẳng lớp Java `com.android.sdklib.tool.AvdManagerCli`
  (xem `scripts/avd-create.sh`).
- Profile `pixel_6` + API 36 ghi `disk.dataPartition.path=<temp>` ⇒ userdata 6 GB nằm trong `%TEMP%` (ổ C:) và mất khi
  tắt. `avd-create.sh` xóa dòng này.
- `android emulator start|list` **không đọc `ANDROID_AVD_HOME`** ⇒ dùng `scripts/emu-start.sh` (gọi `emulator.exe`).
- Emulator tự lấy múi giờ máy chủ (Windows "SE Asia Standard Time" ⇒ `Asia/Bangkok`) ⇒ `emu-start.sh` truyền
  `-timezone Asia/Ho_Chi_Minh`.

## 2. Ma trận AVD

| AVD | Android (API) | Thiết bị | Màn hình | RAM | Vai trò |
|---|---|---|---|---|---|
| `hc-api36` | 16 (36) | pixel_6 | 1080×2400, 420 dpi | 2 GB | Máy chính: targetSdk, giới hạn khởi chạy nền mới nhất |
| `hc-api34` | 14 (34) | pixel_4a | 1080×2340 | 2 GB | Giới hạn full-screen intent của Android 14 |
| `hc-api29` | 10 (29) | small_phone | 720×1280, 320 dpi | 1,5 GB | minSdk; màn nhỏ độ phân giải thấp ~ máy cũ của người cao tuổi |

Ảnh hệ thống **Google Play** (gần máy thật nhất: Play Services, FCM, TTS Google). Không root được — mọi thiết lập
dùng lệnh shell không cần root.

**Hồ sơ "người cao tuổi"** (áp dụng khi test UI): `settings put system font_scale 1.3` và `2.0`;
`wm density` lớn hơn (Cỡ hiển thị); TalkBack bật tay qua Cài đặt (thử E7, E8 bằng giọng đọc).

## 3. Chạy máy ảo

```bash
bash scripts/emu-start.sh hc-api36             # có cửa sổ — thao tác tay, quay video
bash scripts/emu-start.sh hc-api34 --headless  # không cửa sổ — test tự động
adb emu kill                                   # tắt
```
`emu-start.sh` chờ `sys.boot_completed`, đặt múi giờ VN, `system_locales=vi-VN` (có hiệu lực sau lần khởi động lại
kế tiếp — chỉ cần một lần vì userdata được giữ), cỡ chữ 1.0, màn hình luôn sáng.
**Mỗi lúc chỉ chạy 1 AVD** (RAM trống trên máy dev ~3 GB khi các stack khác đang chạy).

## 4. Smoke test đã đạt (08/10/2026)

| Kiểm tra | hc-api36 | hc-api34 | Lệnh |
|---|---|---|---|
| Boot nguội lần đầu | ~27 s (RAM trống ~2,8 GB) | 234 s (RAM trống ~0,7 GB) | `bash scripts/emu-start.sh <avd> --headless` |
| Mô phỏng cuộc gọi đến | ✓ `mCallState=1`, số gọi đến đúng | ✓ | `adb emu gsm call <số hư cấu>` / `gsm cancel` |
| Có `cmd role`, `cmd appops`, `cmd locale` | ✓ | — | cấp vai trò/quyền đặc biệt bằng adb |
| Cỡ chữ 2.0 | ✓ | — | `settings put system font_scale 2.0` |
| Ngôn ngữ vi-VN (không root) | ✓ sau khởi động lại | đặt, chờ lần khởi động sau | `settings put system system_locales vi-VN` |
| Múi giờ VN | ✓ | ✓ | `cmd alarm set-timezone Asia/Ho_Chi_Minh` / cờ `-timezone` |
| Cây UI (Android CLI) | — | ✓ JSON, có nút/nhãn/toạ độ | `android layout --flat` |
| Chụp màn hình | ✓ | ✓ | `adb exec-out screencap -p` / `android screen capture --output=…` |

**App khung (P0-06) trên hc-api36:** `:app` + `:demobank` cài và mở được; màn "Xin chào" đọc được ở cỡ chữ 200%
(ảnh `D:/Android/g0-hello-api36*.png`). Cài APK mất 3 phút 37 giây khi máy ảo + daemon Gradle chạy cùng lúc với
~0,9 GB RAM trống; khi RAM thấp, hệ thống hay báo "Digital Wellbeing/Pixel Launcher không phản hồi" (không phải lỗi app).

hc-api29 chưa boot thử (làm ở P1-S1). Thời gian boot phụ thuộc mạnh vào RAM trống ⇒ dừng stack Docker khác khi làm
Android (`scripts/stop-other-stacks.sh`, P0-06).

## 5. Kịch bản mô phỏng (`scripts/emu-scenario.py`, task P1-S1)

| Tình huống | Cách mô phỏng |
|---|---|
| Cuộc gọi đến từ số lạ / số bị gắn cờ | `adb emu gsm call <số>` → `gsm accept` → `gsm cancel` (số **hư cấu** trong `data/fixtures/`) |
| Mở app ngân hàng | `adb shell monkey -p vn.hoicon.demobank -c android.intent.category.LAUNCHER 1` |
| Đo độ trễ | logcat tag `HC_TIMING` (`app_foreground`, `risk_detected`, `pause_shown`) |
| Kiểm tra màn hình | `android layout` (cây UI) / UI Automator; `android screen capture` |
| Cấp quyền tự động | `cmd role add-role-holder android.app.role.CALL_SCREENING <pkg>`; `appops set <pkg> GET_USAGE_STATS allow`; `appops set <pkg> SYSTEM_ALERT_WINDOW allow`; `pm grant <pkg> android.permission.POST_NOTIFICATIONS` |
| Mất mạng | `svc wifi disable; svc data disable` |
| Doze / standby | `dumpsys deviceidle force-idle`; `am set-standby-bucket <pkg> rare` |
| App bị kill | `am kill <pkg>` |
| Cài app ngoài Play (R2) | `adb install -i com.android.chrome <apk>` |
| Quay video Vòng 1 | `adb emu screenrecord start --time-limit 180 <file>` hoặc ghi cửa sổ emulator bằng OBS |

## 6. Giới hạn của máy ảo (phải nói rõ trong thuyết minh & rủi ro)

- **Không** tái hiện việc Xiaomi/Oppo/Vivo/Samsung diệt tác vụ nền, chế độ tiết kiệm pin riêng của hãng.
- App ngân hàng Việt Nam thật thường **từ chối chạy trên máy ảo/máy root** ⇒ dùng `:demobank`.
- Cuộc gọi là giả lập modem: không có âm thanh thật, không có VoLTE/hai SIM.

**Giảm thiểu:** (a) thiết kế phòng thủ — FGS trong cửa sổ rủi ro, heartbeat báo "mất bảo vệ", thông báo dự phòng sau
cuộc gọi; (b) **Firebase Test Lab** (máy vật lý) trước M2 cho test instrumentation UsageStats + mở SafePause;
(c) `android device remote` (Android Device Streaming, cần dự án Google Cloud + `android auth`) để thao tác máy thật từ
xa; (d) máy của gia đình thí điểm + số liệu heartbeat; (e) **khuyến nghị mua máy Android cũ 1–2 triệu trước 06/12**.
Không tuyên bố tương thích hãng nào chưa thử.
