# HỏiCon — Android ("Lính gác")

Khung P0-06: chạy được, **chưa có tính năng cảm biến** (spike P1-S1). Kiến trúc: `docs/ARCHITECTURE.md` §3; máy ảo:
`docs/EMULATOR.md`; quyền & Play: `docs/PLAY-POLICY.md`.

## Module

| Module | Loại | Nội dung |
|---|---|---|
| `:rules` | Kotlin/JVM thuần (không phụ thuộc Android) | `vn.hoicon.rules` — luật tất định; hiện có `RiskLevel` (khớp `rule_floor` trong `docs/schemas/risk_event.v1.json`, có test hợp đồng) |
| `:app` | Ứng dụng `vn.hoicon.sentinel` "HỏiCon" | Compose + Material 3, màn "Xin chào" tạm; phụ thuộc `:rules`; chưa xin quyền nào |
| `:demobank` | Ứng dụng `vn.hoicon.demobank` "Ngân hàng Mẫu" | App ngân hàng **giả** để thử trên máy ảo/demo; ghi rõ "ỨNG DỤNG DEMO", nút "Chuyển tiền" không làm gì |

Phiên bản: Gradle 9.8.1 (wrapper) · AGP 9.4.1 (Kotlin tích hợp sẵn) · Kotlin 2.4.20 · Compose BOM 2026.06.01 ·
minSdk 29 · compile/targetSdk 36 — xem `gradle/libs.versions.toml`.

## Lệnh (Git Bash, từ gốc repo)

```bash
export GRADLE_USER_HOME=D:/.gradle ANDROID_HOME=D:/Android/Sdk   # JDK 21 cho Gradle khai báo trong D:/.gradle/gradle.properties

apps/android/gradlew -p apps/android :rules:test                               # unit test luật (không cần máy ảo)
apps/android/gradlew -p apps/android :app:assembleDebug :demobank:assembleDebug  # build APK debug

bash scripts/emu-start.sh hc-api36 --headless                                  # 1 máy ảo mỗi lúc (RAM)
apps/android/gradlew -p apps/android :app:installDebug :demobank:installDebug
D:/Android/Sdk/platform-tools/adb.exe shell monkey -p vn.hoicon.sentinel -c android.intent.category.LAUNCHER 1
D:/Android/Sdk/platform-tools/adb.exe emu kill
```

`local.properties` (`sdk.dir=D\:/Android/Sdk`) chỉ ở máy cục bộ, không commit. RAM ít: `gradle.properties` giữ heap 1,5 GB,
biên dịch Kotlin trong daemon Gradle và tắt daemon sau 15 phút rảnh; nếu vẫn thiếu bộ nhớ thêm
`--no-daemon --max-workers=2`, hoặc `gradlew --stop` trước khi bật máy ảo.
