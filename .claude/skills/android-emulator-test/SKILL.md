---
name: android-emulator-test
description: Kiểm thử app Lính gác HỏiCon trên máy ảo Android (AVD hc-api36/hc-api34/hc-api29) — khởi động emulator, cài APK, cấp vai trò sàng lọc cuộc gọi và quyền đặc biệt bằng adb, giả lập cuộc gọi đến, mở app Ngân hàng Mẫu, đo độ trễ phát hiện → dừng an toàn, đọc cây giao diện/chụp màn hình bằng Android CLI, mô phỏng mất mạng/Doze/app bị kill. Dùng sau mọi thay đổi code cảm biến/UI Android, khi chạy spike S1/S2 và trước gate.
---

# android-emulator-test

Công cụ (đường dẫn tuyệt đối, Bash):
- `ADB=D:/Android/Sdk/platform-tools/adb.exe`
- `EMU=D:/Android/Sdk/emulator/emulator.exe`
- `ACLI=D:/Android/Sdk/cmdline-tools/latest/bin/android.exe` (Android CLI: `layout`, `screen capture|resolve`, `docs`).
  **Không** dùng `android emulator start|list` — nó không đọc `ANDROID_AVD_HOME` (AVD nằm ở `D:/Android/avd`).

Chi tiết và lý do ở `docs/EMULATOR.md`.

## 1. Khởi động (mỗi lúc chỉ 1 AVD — RAM máy hạn chế)
```bash
bash scripts/emu-start.sh hc-api36 --headless   # chờ boot xong; đặt giờ VN, vi-VN, cỡ chữ 1.0, màn hình luôn sáng
$ADB devices                                    # phải thấy emulator-5554  device
# bỏ --headless khi cần cửa sổ (quay video, thao tác tay); --cold để bỏ qua snapshot
$ADB emu kill                                   # tắt khi xong
```
Nếu RAM thiếu: đề nghị Minh chạy `bash scripts/stop-other-stacks.sh` (có liệt kê container trước).

## 2. Cài và cấp quyền (gói `vn.hoicon.sentinel`, demo `vn.hoicon.demobank`)
```bash
apps/android/gradlew -p apps/android :app:installDebug :demobank:installDebug
PKG=vn.hoicon.sentinel
$ADB shell cmd role add-role-holder android.app.role.CALL_SCREENING $PKG
$ADB shell appops set $PKG GET_USAGE_STATS allow
$ADB shell appops set $PKG SYSTEM_ALERT_WINDOW allow
$ADB shell pm grant $PKG android.permission.POST_NOTIFICATIONS
$ADB shell cmd role get-role-holders android.app.role.CALL_SCREENING   # xác nhận
```

## 3. Kịch bản chuẩn (hoặc `python scripts/emu-scenario.py --avd hc-api36 --scenario fake_police`)
```bash
$ADB logcat -c
$ADB emu gsm call 0900000001            # số HƯ CẤU — không dùng số thật
sleep 3 && $ADB emu gsm accept 0900000001
$ADB shell monkey -p vn.hoicon.demobank -c android.intent.category.LAUNCHER 1
sleep 4
$ADB logcat -d -s HC_TIMING:I            # mốc: risk_detected / pause_shown → độ trễ
$ACLI layout --flat --output=$TEMP/layout.json && /usr/bin/grep -o '"text":"[^"]*Hỏi con[^"]*"' $TEMP/layout.json; rm -f $TEMP/layout.json
#   ↑ ghi ra file: stdout trên console Windows làm vỡ dấu tiếng Việt. Trong vòng lặp until/while dùng /usr/bin/grep
#     (RTK viết lại `grep` thành `rtk grep`, không hiểu -q ⇒ vòng lặp treo).
$ACLI screen capture --output=docs/spikes/shots/pause-api36.png   # --annotate để đánh số phần tử
$ADB emu gsm cancel 0900000001
```
Đạt khi: màn `SafePauseActivity` hiện, độ trễ `pause_shown - app_foreground ≤ 3000 ms`, sự kiện nằm trong outbox (và lên backend nếu đang chạy).

## 4. Điều kiện khắc nghiệt
- Mất mạng: `$ADB shell svc wifi disable; $ADB shell svc data disable` → dừng an toàn vẫn phải hiện; bật lại thì outbox gửi bù.
- Doze/standby: `$ADB shell dumpsys deviceidle force-idle`; `$ADB shell am set-standby-bucket $PKG rare`.
- App bị kill: `$ADB shell am kill $PKG` rồi chạy lại kịch bản.
- Cài ngoài Play (luật R2): `$ADB install -i com.android.chrome <apk-thử>` ngay sau cuộc gọi lạ.
- Cỡ chữ lớn: `$ADB shell settings put system font_scale 2.0` (nhớ trả về 1.0).

## 5. Ghi kết quả
- Cập nhật `docs/spikes/device-matrix.md`: AVD/API, kịch bản, số lần chạy, p50/p95 độ trễ, đạt/không, ảnh chụp.
- Ghi rõ đây là **máy ảo**; không suy ra hành vi máy thật của Samsung/Xiaomi/Oppo.
- Không commit bản dump `android layout` / logcat thô: chúng chứa số gọi đến (trong thông báo hệ thống). Chỉ lưu số đo + ảnh.
