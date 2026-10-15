# Quickstart: kiểm tay spec 001 (máy Linux của Tiến, worktree `../hoicon-wt/android`)

```bash
cd ~/Projects/hoicon-wt/android
. scripts/android-env.sh
bash scripts/emu-start.sh hc-api36 --headless          # một emulator mỗi lúc
apps/android/gradlew -p apps/android :rules:test :app:assembleDebug :demobank:assembleDebug

# US1 — bộ đo trên AVD trước (FR-001), rồi FTL (FR-002/003)
apps/android/gradlew -p apps/android :latency:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.runs=10 -Pandroid.testInstrumentationRunnerArguments.variant=view
bash scripts/ftl-latency.sh model=<samsung-a>,version=34      # cần gcloud + Firebase (W0-3)

# US2 — dự phòng không SAW (FR-006)
$ADB shell appops set vn.hoicon.sentinel SYSTEM_ALERT_WINDOW deny
python scripts/emu-scenario.py --avd hc-api36 --scenario fake_police --runs 5
$ADB logcat -d -v epoch -s HC_TIMING HC_SPIKE | grep -E 'fsi=|app_foreground|tts_'
$ADB shell appops set vn.hoicon.sentinel SYSTEM_ALERT_WINDOW allow

# US3 — ảnh 100%/200% (FR-007/008)
$ADB shell settings put system font_scale 2.0   # rồi chụp: $ACLI screen capture …

# Hồi quy (FR-010)
python scripts/emu-scenario.py --avd hc-api36 --scenario fake_police --runs 10
```
Lặp các bước máy ảo với `hc-api34`. Ghi mọi số vào `evidence.md` theo mẫu.
