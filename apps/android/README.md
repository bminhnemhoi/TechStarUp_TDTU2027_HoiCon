# HỏiCon — Android ("Lính gác")

Spike P1-S1: chuỗi cảm biến tối thiểu để đo (cuộc gọi số lạ → cửa sổ rủi ro → app ngân hàng → SafePause), kết quả ở
`docs/spikes/P1-S1-cam-bien.md`. Kiến trúc: `docs/ARCHITECTURE.md` §3; máy ảo: `docs/EMULATOR.md`; quyền & Play:
`docs/PLAY-POLICY.md`.

## Module

| Module | Loại | Nội dung |
|---|---|---|
| `:rules` | Kotlin/JVM thuần (không phụ thuộc Android) | `vn.hoicon.rules` — `RiskLevel`, `RiskEngine` (R0, R1 + biến thể critical, cửa sổ 10 phút, không dưới `floor`), `PhoneHasher` (E.164 VN + `h1` + `last3`); test hợp đồng với `risk_event.v1.json` |
| `:app` | Ứng dụng `vn.hoicon.sentinel` "HỏiCon" | `sensing/`: `HcCallScreeningService` (chỉ quan sát), `RiskWindowService` (FGS `specialUse`, quét UsageStats 1 s), `CallStateMonitor` (H2), mốc `HC_TIMING`; `pause/`: `SafePauseActivity` (giữ 3 s để tiếp tục, TTS vi-VN); `MainActivity` = màn quyền cho nhà phát triển |
| `:demobank` | Ứng dụng `vn.hoicon.demobank` "Ngân hàng Mẫu" | App ngân hàng **giả** để thử trên máy ảo/demo; ghi rõ "ỨNG DỤNG DEMO", nút "Chuyển tiền" không làm gì |

Phiên bản: Gradle 9.8.1 (wrapper) · AGP 9.4.1 (Kotlin tích hợp sẵn) · Kotlin 2.4.20 · Compose BOM 2026.06.01 ·
minSdk 29 · compile/targetSdk 36 — xem `gradle/libs.versions.toml`.

## Lệnh (Git Bash, từ gốc repo)

```bash
export GRADLE_USER_HOME=D:/.gradle ANDROID_HOME=D:/Android/Sdk   # JDK 21 cho Gradle khai báo trong D:/.gradle/gradle.properties

apps/android/gradlew -p apps/android :rules:test                               # unit test luật (không cần máy ảo)
apps/android/gradlew -p apps/android :app:assembleDebug :demobank:assembleDebug  # build APK debug

bash scripts/emu-start.sh hc-api36 --headless                                  # 1 máy ảo mỗi lúc (RAM)
apps/android/gradlew -p apps/android --stop                                    # nhả RAM trước khi cài
ADB=D:/Android/Sdk/platform-tools/adb.exe
$ADB install -r apps/android/app/build/outputs/apk/debug/app-debug.apk
$ADB install -r apps/android/demobank/build/outputs/apk/debug/demobank-debug.apk
$ADB shell cmd role add-role-holder android.app.role.CALL_SCREENING vn.hoicon.sentinel
$ADB shell appops set vn.hoicon.sentinel GET_USAGE_STATS allow
$ADB shell appops set vn.hoicon.sentinel SYSTEM_ALERT_WINDOW allow
$ADB shell pm grant vn.hoicon.sentinel android.permission.POST_NOTIFICATIONS
python scripts/emu-scenario.py --scenario fake_police --runs 10                # đo độ trễ (mốc HC_TIMING)
$ADB emu kill
```

Mốc đo: logcat tag `HC_TIMING`, dạng `HC_TIMING: <mốc> <epoch ms>` — `call_screened`, `window_opened`
(`window_opened_bg`/`fgs_denied` nếu không mở được FGS), `app_foreground` (= timestamp UsageEvent), `risk_detected`,
`pause_resumed`, `pause_shown` (frame đầu), `tts_started`, `pause_fallback`, `audio_mode_<n>`, `tel_state_<n>`,
`app_in_front_on_connect` (GAP: app tài chính mở sẵn trước cuộc gọi), `pause_obscured` (chạm bị app khác che, đã bỏ),
`pause_continued` (+ `HC_SPIKE: continue_via=hold|a11y`). Chỉ ghi ở bản **debug** (`BuildConfig.DEBUG`), kể cả h1 demo và
công tắc A/B `files/spike_compose_pause`. GAP: `python scripts/emu-scenario.py --scenario bank_first --runs 5`.

`local.properties` (`sdk.dir=D\:/Android/Sdk`) chỉ ở máy cục bộ, không commit. RAM ít: `gradle.properties` giữ heap 1,5 GB,
biên dịch Kotlin trong daemon Gradle và tắt daemon sau 15 phút rảnh; nếu vẫn thiếu bộ nhớ thêm
`--no-daemon --max-workers=2`, hoặc `gradlew --stop` trước khi bật máy ảo.
