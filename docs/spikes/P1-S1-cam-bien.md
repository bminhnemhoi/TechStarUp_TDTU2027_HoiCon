# Spike P1-S1 — Chuỗi cảm biến "cuộc gọi lạ → app ngân hàng → dừng an toàn" trên máy ảo

- Thời gian: 08–24/10/2026 (bắt đầu sớm sau G0) · Chủ trì: `android-engineer` · Nhánh `feat/p1-s1-sensors`
- Ngưỡng đạt (ROADMAP): bắt **10/10** cuộc gọi lạ; phát hiện → SafePause **p95 ≤ 3 s**; vẫn chạy sau khi app bị kill;
  có phương án dự phòng cho từng mắt xích. Kết quả ghi vào cuối file này (mục "Kết quả") + `docs/spikes/device-matrix.md`.
- **Mọi số đo là máy ảo** — không suy ra hành vi máy thật của Samsung/Xiaomi/OPPO (xem `docs/EMULATOR.md` §6).

## Cơ sở từ tài liệu chính thức (Android Knowledge Base, tra 08/10/2026)

| Sự kiện nền tảng | Nguồn (`android docs fetch …`) | Hệ quả thiết kế |
|---|---|---|
| `CallScreeningService.onScreenCall()` được gọi cho cuộc gọi đến/đi **khi số KHÔNG có trong danh bạ** (app giữ vai trò `CALL_SCREENING`) | `kb://android/develop/connectivity/telecom/dialer-app/screen-calls` | Tín hiệu "số lạ" **không cần `READ_CONTACTS`/`READ_CALL_LOG`** (đúng ADR-001) |
| Khởi chạy activity từ nền được phép khi app **được cấp `SYSTEM_ALERT_WINDOW`** | `kb://android/guide/components/activities/secure-bal` | `SafePauseActivity` mở trực tiếp từ service — không vẽ overlay lên app ngân hàng |
| Từ API 34/35: `PendingIntent` cần opt-in BAL của bên gửi/bên tạo | như trên | Không dựa vào `PendingIntent` để mở SafePause; nếu dùng (thông báo) phải đặt `MODE_BACKGROUND_ACTIVITY_START_ALLOWED` |
| Khởi động foreground service từ nền bị cấm, trừ ngoại lệ: app **khởi chạy được activity từ nền**; người dùng **tắt tối ưu pin**; có `SYSTEM_ALERT_WINDOW` (target ≥ 35: **phải đang có overlay hiển thị**); FCM ưu tiên cao; người dùng thao tác thông báo… | `kb://android/develop/background-work/services/fgs/restrictions-bg-start` | Mở cửa sổ rủi ro (FGS) từ `onScreenCall` là **điểm rủi ro số 1** của spike — phải đo trên API 36/34/29 |
| FGS phải khai báo type (API 34+); `specialUse` cần thuộc tính mô tả mục đích + giải trình với Play | `kb://android/develop/background-work/services/fgs/service-types` | `<property android:name="android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE" …>` |

## Giả thuyết cần kiểm

| # | Giả thuyết | Cách kiểm | Dự phòng nếu sai |
|---|---|---|---|
| H1 | `onScreenCall` nhận **100%** cuộc gọi từ số lạ (10/10), kể cả khi app đã bị kill | `adb emu gsm call` × 10, có/không `am kill` | thông báo sau cuộc gọi (`READ_PHONE_STATE`) |
| H2 | Biết được cuộc gọi **đang diễn ra / vừa kết thúc** mà không cần quyền nhạy cảm | so `AudioManager.mode == MODE_IN_CALL` (không quyền) với `TelephonyCallback.CallStateListener` (`READ_PHONE_STATE`) | dùng `READ_PHONE_STATE` (được Play cho phép, không thuộc nhóm bị cấm) |
| H3 | Từ `onScreenCall` khởi động được **FGS `specialUse`** ("HỏiCon đang bảo vệ") trên API 36/34/29 | thử 3 đường: (a) có SAW, (b) SAW + tắt tối ưu pin, (c) không SAW — ghi `ForegroundServiceStartNotAllowedException` | xin người dùng tắt tối ưu pin ở E3; hoặc `WorkManager` expedited + thông báo |
| H4 | Trong cửa sổ rủi ro, `UsageStatsManager.queryEvents` (quét 1 s) thấy app ngân hàng lên tiền cảnh trong **≤ 1,2 s** | mốc `app_foreground` (timestamp sự kiện) vs `risk_detected` | quét 500 ms trong 2 phút đầu |
| H5 | `startActivity(SafePause)` từ service khi đã có SAW hiện trên **app ngân hàng** trong **≤ 800 ms** | mốc `pause_shown` (onResume + frame đầu) | thông báo full-screen intent / heads-up + TTS |
| H6 | Đường găng không dùng mạng/LLM: tắt mạng vẫn đạt H4–H5 | `svc wifi/data disable` | — (bắt buộc) |

## Thiết kế tối thiểu (chỉ đủ để đo — không phải UI cuối)

```
:rules (JVM)   RiskEngine: CallSignal + AppForeground ⇒ Decision(level = rule_floor, ruleId)
               R0 trusted ⇒ none · R1 số lạ/đang hoặc ≤10' sau gọi + app bank/wallet ⇒ high (critical nếu flagged hoặc gọi >5')
:app           HcCallScreeningService  → onScreenCall: chỉ quan sát (allow), ghi CallSignal, mở RiskWindowService
               RiskWindowService (FGS specialUse, chip "HỏiCon đang bảo vệ") → quét UsageStats 1 s ≤ 10'
               → RiskEngine → SafePauseActivity (toàn màn hình, nút "Hỏi con" + "Tiếp tục" giữ 3 s, TTS tiếng Việt)
               Mốc logcat HC_TIMING: call_screened, window_opened, app_foreground, risk_detected, pause_shown
               PermissionsScreen (dev): cấp vai trò/SAW/usage stats/thông báo + nút mở cài đặt pin
:demobank      app ngân hàng mẫu (đã có)
```
- Danh sách app ngân hàng trong spike: `vn.hoicon.demobank` + vài gói thật (danh sách đầy đủ ở P1-S2,
  `data/bank_apps.vn.json`). Khai báo `<queries>` theo gói — **không** `QUERY_ALL_PACKAGES`.
- Số điện thoại: chỉ giữ trong bộ nhớ; log chỉ `last3`; `h1` tính bằng `:rules` (`PhoneHasher`).
- Chuỗi chữ: tiếng Việt, giọng ấm, không gây hoảng (bản nháp — `ux-elder-reviewer` duyệt ở P2-05).

## Quy trình đo
1. `bash scripts/emu-start.sh hc-api36 --headless` (hỏi Minh trước nếu cần dừng stack khác để có RAM).
2. Cài `:app` + `:demobank`; cấp quyền bằng adb (skill `android-emulator-test` §2).
3. `python scripts/emu-scenario.py --scenario fake_police --runs 10` ⇒ p50/p95 `pause_shown − app_foreground`.
4. Lặp với: app bị kill trước cuộc gọi; mất mạng; Doze (`dumpsys deviceidle force-idle`); không SAW; API 34, 29.

## Kết quả
_(điền khi chạy — bảng: AVD · kịch bản · n · bắt được · p50 · p95 · ghi chú)_
