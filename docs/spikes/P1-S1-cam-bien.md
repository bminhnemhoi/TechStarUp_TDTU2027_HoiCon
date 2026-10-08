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

## Kết quả (đo 08/10/2026, **chỉ trên máy ảo**)

### Điều kiện đo — đọc trước khi dùng số
- AVD `hc-api36` (Android 16, BE2A.250530), `hc-api34` (Android 14), `hc-api29` (Android 10); ảnh Google Play, chạy
  headless, mỗi lúc 1 máy ảo. APK **debug** (không R8), biên dịch AOT trên máy ảo bằng `cmd package compile -m speed -f`
  (gần với bản cài từ Play). Biến thể quyền mặc định = **(b)**: vai trò CALL_SCREENING + usage access + SAW + thông báo
  + tắt tối ưu pin (`dumpsys deviceidle whitelist +`), `READ_PHONE_STATE` cấp để so sánh H2 (trừ API 29).
- Máy chủ chỉ còn **0,6–1,8 GB RAM trống**; trong máy ảo API 36 tải trung bình 5–35, zram swap ~0,9 GB. **Đối chứng**:
  mở app Compose tầm thường `:demobank` bằng `am start -W` trên API 36 cùng lúc: nguội p50 6 269 ms / p95 10 911 ms,
  ấm p50 4 258 ms (n=3). ⇒ Độ trễ tuyệt đối dưới đây **bị môi trường thổi phồng**; không suy ra máy thật.
- Độ trễ = mốc `HC_TIMING` (epoch ms): phát hiện = `risk_detected − app_foreground` (timestamp UsageEvent); mở =
  `pause_shown − risk_detected`; SafePause = `pause_shown − app_foreground` (frame đầu, `registerFrameCommitCallback`).
  p95 theo hạng gần nhất ⇒ với n=10, p95 = giá trị lớn nhất. "Nguội" = `am force-stop` trước mỗi cuộc gọi (tiến trình do
  Telecom khởi lại, SafePause là UI đầu tiên của tiến trình — tình huống thực tế hay gặp); "ấm" = tiến trình còn sống.
- Lệnh: `python scripts/emu-scenario.py --scenario {screen_only|call_state|fake_police|launch_baseline} --runs N
  --prep {none|kill|force-stop}`. Log/ảnh thô để ngoài repo (`D:/Android/s1-*`).

### Bảng số đo

| AVD | Kịch bản | n | Bắt được | p50 (ms) | p95 (ms) | Ghi chú |
|---|---|---|---|---|---|---|
| api36 | H1 `screen_only`, app sống | 10 | 10/10 `call_screened`, 10/10 FGS | — | — | |
| api36 | H1 `screen_only`, `am kill` trước gọi | 10 | 10/10, FGS 10/10 | — | — | tiến trình chết thật (`pidof` rỗng) |
| api36 | H1 `screen_only`, `force-stop` trước gọi | 10 | 10/10, FGS 10/10 | — | — | xem rủi ro "hết hạn sàng lọc 5 s" |
| api36 | H3 (a) SAW, tối ưu pin **bật** | 5 | 5/5 sàng lọc · **FGS 0/5** | — | — | `Background started FGS: Disallowed … code:DENIED`, chạy dịch vụ nền dự phòng |
| api36 | H3 (c) không SAW, tối ưu pin bật | 5 | 5/5 · FGS 0/5 | — | — | như (a) |
| api36 | H3 (d) không SAW, tối ưu pin **tắt** | 5 | 5/5 · **FGS 5/5** | — | — | `code:SYSTEM_ALLOW_LISTED` |
| api36 | (a) + mở ngân hàng sau 75–90 s | 1 | **0/1** | — | — | dịch vụ nền bị dừng ở giây 59 ("Stopping service due to app idle"), tiến trình bị đóng băng |
| api36 | (d) không SAW: đường dự phòng | 1 | 1/1 thông báo | — | — | `BAL_BLOCK`; watchdog 1,5 s ⇒ heads-up sau 2 458 ms, câu nói TTS sau 3 030 ms (tính từ `app_foreground`) |
| api36 | H2 `call_state` (audio − telephony) | 5 | 5/5 đủ 3 chuyển trạng thái | chuông +311 · nhấc +1 149 · kết thúc +1 971 | chuông +907 · nhấc +2 195 · kết thúc +4 320 | audio mode luôn trễ hơn, không bao giờ bỏ sót |
| api36 | H4/H5 `fake_police`, ấm (lô 1) | 10 | 10/10 | phát hiện 517 · SafePause 1 462 | 923 · **7 380** | 9/10 ≤ 3 s; lần ngoại lai là lần đầu của lô |
| api36 | H4/H5 `fake_police`, ấm (lô 2) | 10 | 10/10 | phát hiện 606 · mở 712 · SafePause 1 378 | 1 546 · 5 564 · **7 110** | 9/10 ≤ 3 s; lần đầu lô: mở 5,6 s |
| api36 | `fake_police` nguội, UI Compose | 10 | 10/10 | phát hiện 942 · mở 3 177 · SafePause 4 187 | 2 476 · 4 351 · 6 375 | **0/10 ≤ 3 s**; `pause_resumed` sau ~0,6 s, frame đầu Compose ~3 s ("Davey 3014ms") |
| api36 | H6 tắt mạng (wifi+data), nguội, Compose | 10 | 10/10 | phát hiện 766 · mở 3 248 · SafePause 4 043 | 1 247 · 4 317 · 5 288 | như khi có mạng; TTS vi-VN vẫn nói (giọng offline) |
| api36 | Doze ép (`force-idle`), ấm | 3 | 3/3 | mở 643 · SafePause 1 035 | 759 · 1 637 | app đã được miễn tối ưu pin |
| api36 | A/B nguội — UI **View thuần** | 10 | 10/10 | mở 2 119 · SafePause 2 782 | 5 485 · 6 216 | 6/10 ≤ 3 s |
| api36 | A/B nguội — UI **Compose** (xen kẽ) | 10 | 9/10 | mở 2 892 · SafePause 3 626 | 5 015 · 8 580 | 3/9 ≤ 3 s; 1 lần không có mốc nào (trước khi có bộ chẩn đoán) |
| api34 | H3 (a) SAW, tối ưu pin bật | 5 | 5/5 · **FGS 5/5** | — | — | Android 14: SAW một mình là đủ |
| api34 | H3 (c) không SAW | 5 | 5/5 · FGS 0/5 | — | — | |
| api34 | H3 (b) SAW + tắt tối ưu pin | 5 | 5/5 · FGS 5/5 | — | — | |
| api34 | H1 `am kill` / sống / `force-stop` | 10+10+10 | 30/30 | — | — | |
| api34 | H2 `call_state` | 3 | 3/3 | chuông +126 · nhấc +608 · kết thúc +1 686 | +149 · +655 · +2 398 | |
| api34 | `fake_police` nguội, View | 30 | 23/23 cuộc gọi Telecom nhận được | phát hiện 723 · mở 1 987 · SafePause 2 620 | 2 190 · 3 272 · 5 926 | 15/23 ≤ 3 s; **7 lần lỗi modem giả lập** (xem dưới) |
| api34 | `fake_police` ấm, View | 10 | 10/10 | phát hiện 799 · mở 433 · SafePause 1 135 | 962 · 8 806 · 9 768 | 8/10 ≤ 3 s; lần đầu lô 9,8 s |
| api29 | H1+H3 `force-stop` (không SAW cần cho FGS) | 5 | 5/5 · FGS 5/5 | — | — | Android 10 chưa có giới hạn FGS nền |
| api29 | H2 (PhoneStateListener **không quyền**) | 3 | 3/3 | chuông +420 · nhấc +651 · kết thúc +1 852 | +703 · +661 · +1 888 | audio quét 1 s |
| api29 | `fake_police` nguội, View | 5 | 5/5 | phát hiện 906 · mở 759 · SafePause 1 665 | 929 · 1 617 · **2 132** | **5/5 ≤ 3 s** |
| api29 | `fake_police` ấm, View | 5 | 5/5 | phát hiện 864 · mở 1 403 · SafePause 2 177 | 1 106 · 2 598 · 3 486 | 4/5 ≤ 3 s |

Lỗi môi trường đã loại khỏi tỉ lệ "bắt được" (có bằng chứng log radio): sau khi **nhấc máy** rồi `adb emu gsm cancel`,
modem giả lập không báo kết thúc ⇒ `GsmCdmaCallTracker` kẹt OFFHOOK tới lần `RING` kế tiếp (lúc đó `+CLCC` rỗng) ⇒
cuộc gọi đó không bao giờ tới Telecom (`IncomingCallFilterGraph` vắng). Chỉ gặp trên api34 và chỉ ở kịch bản có nhấc máy
(`screen_only` không nhấc máy: 30/30). Script ghi nguyên nhân từng lần trượt (`screening_diagnosis`).

### Kết luận từng giả thuyết

- **H1 — ĐÚNG trên máy ảo (có điều kiện).** 10/10 ở cả 3 trạng thái (sống / `am kill` / `force-stop`) trên api36 và
  api34, 5/5 trên api29 — vai trò CALL_SCREENING khởi lại tiến trình đã chết. **Điều kiện:** Telecom chỉ chờ sàng lọc
  ~5 s; với APK debug chưa AOT và máy ảo quá tải, 3 lần khởi động nguội trễ hơn hạn đó ⇒ `mCallResponse=null`, không có
  `onScreenCall` (cuộc gọi vẫn đổ chuông bình thường, chỉ là HỏiCon không biết). Sau khi AOT: 95/95 lần sàng lọc trong
  `screen_only` (api36 45, api34 45, api29 5); từ lúc khởi tiến trình tới `onScreenCall` quan sát được 0,3 s (api34) tới
  2,5 s (api36).
- **H2 — ĐÚNG.** `AudioManager.mode` (không cần quyền; API 31+ dùng `OnModeChangedListener`, API 29–30 quét 1 s) bắt đủ
  đổ chuông/nhấc máy/kết thúc ở 11/11 lần trên 3 mức API, chỉ trễ hơn `TelephonyCallback` 0,1–0,9 s (chuông), 0,4–2,2 s
  (nhấc), 1,4–4,3 s (kết thúc) — không đáng kể với cửa sổ 10 phút. API 29–30: `PhoneStateListener` cũng không cần quyền.
  ⇒ **Không cần `READ_PHONE_STATE`.**
- **H3 — SAI trên Android 16 nếu chỉ có SAW.** Từ `onScreenCall` (uid đang ở trạng thái SVC do Telecom bind):
  api36 cần **tắt tối ưu pin** (SAW không đủ vì target 36 đòi overlay đang hiển thị); api34 chỉ cần SAW; api29 không giới
  hạn. Không có FGS thì dịch vụ nền dự phòng sống ~60 s rồi bị dừng + đóng băng ⇒ mở ngân hàng sau đó bị lọt.
- **H4 — ĐÚNG khi ấm, SAI ở đuôi khi nguội.** Phát hiện p50 0,5–0,9 s mọi lô; p95 ≤ 1,1 s ở các lô ấm (trừ 1 lô
  1,5 s), nhưng 1,0–3,6 s ở các lô nguội (máy ảo bận đúng lúc app ngân hàng khởi động). Chưa cần quét 500 ms:
  phần trễ chủ yếu là tick bị hoãn khi hệ thống quá tải, không phải chu kỳ quét.
- **H5 — Mở từ nền ĐÚNG; ≤ 800 ms chỉ ĐÚNG khi tiến trình đã có UI ấm.** `startActivity` từ FGS khi có SAW luôn được
  phép (`BAL_ALLOW…`) và nằm trên task app ngân hàng (task riêng, không overlay). Khâu "mở": ấm p50 0,4–0,7 s trên api36/34
  (đạt; api29 1,4 s), nguội p50 2,0–3,2 s trên api36/34 (trượt; api29 0,76 s) — chi phí là cửa sổ/renderer đầu tiên của
  tiến trình + frame đầu Compose. View thuần nhanh hơn
  Compose ~0,8 s ở trung vị (A/B xen kẽ, cùng máy ảo) nhưng không đủ để đạt 800 ms khi nguội trên máy ảo này.
  Không SAW ⇒ `BAL_BLOCK`, watchdog 1,5 s chuyển sang thông báo heads-up + TTS (đã chạy).
- **Tổng ≤ 3 s (p95) — CHƯA ĐẠT trên máy ảo** ở mọi lô n=10 (p95 = max = 5–10 s, thường là lần đầu lô); đạt ở api29
  nguội (5/5, max 2,1 s). p50 ấm 1,0–1,5 s (api29 2,2 s), p50 nguội 1,7–4,2 s. Với đối chứng mở app tầm thường mất 4–6 s, **số này
  chưa đủ để kết luận cho máy thật** ⇒ phải đo lại trên máy vật lý/Firebase Test Lab (P1-S2) trước khi chốt gate.
- **H6 — ĐÚNG.** Tắt wifi + data (không có mạng mặc định, ping thất bại): 10/10, độ trễ tương đương khi có mạng; TTS
  vi-VN nói được offline. Manifest **không có `INTERNET`** nên đường găng không thể dùng mạng.

### Phát hiện phụ
- TTS Google có vi-VN trên cả 3 AVD (api36: `setLanguage` = 1; api34/29: có `tts_started`, không lần nào
  `tts_unavailable`); **khởi tạo nguội 5,6–13 s** (api36) ⇒ khởi động sẵn
  (`Speaker.warmUp`) khi mở cửa sổ rủi ro là bắt buộc; nhờ vậy câu nói đầu thường bắt đầu *trước* frame đầu của SafePause.
- Thông báo FGS kênh `IMPORTANCE_LOW` bị gom vào mục "Silent", **không có biểu tượng trên thanh trạng thái** ⇒ chưa phải
  "chip đang bảo vệ". Live Updates (chip thật, API 36) theo hướng dẫn là cho hoạt động do *người dùng* khởi xướng — không
  hợp với cuộc gọi do người khác gọi tới.
- Telecom tự gửi `android.telecom.action.POST_CALL` tới app giữ vai trò sàng lọc sau cuộc gọi (log api36: `START
  act=android.telecom.action.POST_CALL … pkg=vn.hoicon.sentinel … result code=-91` vì app chưa có activity này). Tài liệu
  chính thức nhắc `ACTION_POST_CALL` cho màn hình sau cuộc gọi của app sàng lọc ⇒ **ứng viên dự phòng** cho H3 (activity do
  hệ thống mở ⇒ app ở tiền cảnh ⇒ được mở FGS) — chưa thử, điều kiện gửi chưa xác minh.
- Màn SafePause (bản nháp): ở cỡ chữ 200% (api34) và trên màn 720×1280 (api29, cỡ chữ 100%) hai nút nằm dưới mép màn
  hình đầu tiên; thông báo cuộc gọi đến của hệ thống che phần đầu. Giữ 1 s không qua, giữ 3,5 s qua và ghi `pause_continued`,
  lần mở ngân hàng tiếp theo trong cùng cuộc gọi không nhắc lại (đã thử trên api34).

### Phương án dự phòng đề xuất (theo mắt xích)
| Mắt xích | Hỏng khi | Dự phòng |
|---|---|---|
| Biết có số lạ (H1) | Telecom hết hạn 5 s khi khởi động nguội; hãng chặn khởi chạy | giữ khởi động app nhẹ (không `Application` nặng, R8 + baseline profile); heartbeat báo "mất bảo vệ"; thử `ACTION_POST_CALL` |
| Cửa sổ rủi ro (H3) | Android 15+ chưa tắt tối ưu pin | E3 bắt buộc bước "Không giới hạn pin" (màn danh sách, không dùng quyền `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`); heartbeat báo trạng thái; dự phòng ~60 s bằng dịch vụ nền (đã có); thử `ACTION_POST_CALL` |
| Trạng thái cuộc gọi (H2) | OEM đổi hành vi audio mode | `TelephonyCallback` + `READ_PHONE_STATE` chỉ khi máy thật chứng minh cần |
| Phát hiện (H4) | tick bị hoãn khi máy quá tải | giữ 1 s; xem lại 500 ms khi có số máy thật |
| Mở SafePause (H5) | không SAW / hãng chặn BAL / chậm | watchdog 1,5 s ⇒ heads-up + TTS (đã có); E7 bằng View thuần hoặc làm ấm UI khi mở cửa sổ |

### Đề xuất quyết định cho ADR-007 (cơ chế cảm biến)
1. **Số lạ:** `CallScreeningService` (vai trò CALL_SCREENING), chỉ quan sát, luôn cho cuộc gọi đi qua.
2. **Trạng thái cuộc gọi:** `AudioManager.mode` (không quyền); **bỏ `READ_PHONE_STATE`** khỏi manifest sản phẩm.
3. **Cửa sổ rủi ro:** FGS `specialUse` mở từ `onScreenCall`; điều kiện cần trên Android 15+: **miễn tối ưu pin** (quyền
   bắt buộc ở E3 cùng SAW + usage access + vai trò); thông báo kênh `IMPORTANCE_DEFAULT` không âm thanh/rung (kênh
   tắt tiếng — `Notification.Builder` của nền tảng không có `setSilent`) để có biểu tượng trên thanh trạng thái.
4. **Phát hiện:** `UsageStatsManager.queryEvents` mỗi 1 s, `<queries>` theo đúng tên gói của `data/bank_apps.vn.json`.
5. **Dừng an toàn:** `startActivity` trực tiếp từ FGS (miễn trừ BAL nhờ SAW), task riêng, watchdog 1,5 s ⇒ heads-up +
   TTS; TTS làm ấm khi mở cửa sổ. Chọn View thuần hay Compose cho E7 sau khi đo nguội trên máy thật (công tắc A/B tạm:
   `adb shell run-as vn.hoicon.sentinel touch files/spike_compose_pause`).
6. **Gate P1-S1:** 10/10 bắt cuộc gọi — đạt trên máy ảo; p95 ≤ 3 s — **chưa đạt trên máy ảo** (môi trường quá tải),
   cần số máy thật trước G1; sống sót khi bị kill — đạt (api36 cần miễn tối ưu pin để mở FGS).

### Giới hạn
Máy ảo không tái hiện diệt tác vụ nền của Xiaomi/OPPO/Samsung, tự khởi chạy bị chặn, hay âm thanh thật (chạy `-no-audio`:
chưa nghe được TTS trong lúc gọi, chưa kiểm định tuyến âm thanh). Chưa thử TalkBack với thao tác giữ 3 s. Không tuyên bố
tương thích hãng nào.

## Lượt sửa sau review (09/10/2026 — UX người cao tuổi + bảo mật)

| ID | Đã làm | Kiểm chứng |
|---|---|---|
| UX-1 | E7 (View + Compose): chỉ phần chữ cuộn (`weight=1`, thanh cuộn luôn hiện, mép mờ 48 dp), thanh nút ghim đáy, cách thanh cử chỉ ≥ 16 dp, không khóa cỡ chữ | ảnh `D:/Android/s1b-e7-api34-font100/200.png`, `s1b-e7-api29-font100/200.png`: hai nút thấy ngay ở 200% trên 1080×2340 và 720×1280 |
| UX-2 | Nút giữ ngoài vùng cuộn; `requestDisallowInterceptTouchEvent(true)` lúc chạm; xê dịch trong phạm vi nút vẫn tính, trượt ra ngoài = thả sớm. **Phát hiện khi thử:** dòng "Chưa đủ 3 giây…" đặt dưới nút làm cả thanh nút bị đẩy lên (nút dời đi dưới ngón tay) ⇒ dòng phụ "Giữ ngón tay 3 giây" đưa vào trong nút, dòng trạng thái + nút xác nhận đặt **trên** hai nút | api34, cỡ chữ 200%: giữ 1 s ⇒ không tiếp tục, hai nút giữ nguyên vị trí (`s1b-e7-api34-font200-too-short.png`); `input swipe` chậm lệch ~25 dp trong 3,5 s ⇒ `continue_via=hold` |
| UX-3 | Xưng "bác", AI tự xưng "HỏiCon"; tiêu đề/thân/lý do (đang gọi / đã cúp × ngân hàng / ví điện tử / chứng khoán)/nút theo đúng câu chữ được giao; nút phụ "Nghe lại" (viền, 64 dp, góc trên) | ảnh trên |
| UX-4 | 4 câu đọc, mỗi câu 1 utterance, tốc độ 0,9, nghỉ 350 ms (`playSilentUtterance`) | `tts_started` trước frame đầu ở lô hồi quy |
| UX-5 | Thông báo dự phòng: tiêu đề/thu gọn/mở rộng/phụ đề "Trợ lý AI HỏiCon"/nút "Gọi cho con"; câu đọc = UX-4 + câu chỉ chỗ chạm | api34 bỏ SAW: heads-up sau 1 814 ms, câu nói sau 1 960 ms (từ `app_foreground`), ảnh `s1b-fallback-shade-api34.png` |
| UX-6 | Thanh navy đặc 10 dp ở đáy nút (cắt theo viền bo), rung nhẹ lúc bắt đầu giữ và lúc đủ 3 s (`performHapticFeedback`, không cần quyền) | máy ảo không có bộ rung — chưa cảm nhận được |
| UX-7 | Vai trò nút, contentDescription "Vẫn tiếp tục", nhãn ACTION_LONG_CLICK "giữ 3 giây để tiếp tục", dòng trạng thái live region polite, tiêu đề cửa sổ "HỏiCon — Khoan chuyển tiền đã", hoãn TTS 1,5 s khi TalkBack bật | **chưa thử với TalkBack thật** |
| UX-8 | Kênh mới `protecting_v2` mức DEFAULT, tắt âm thanh/rung (xóa kênh LOW cũ — mức kênh không nâng được); câu chữ mới, không lộ "10 phút"; phụ đề AI | api34: biểu tượng khiên trên thanh trạng thái, thông báo ở mục chính (không còn "Silent"), ảnh `s1b-notification-api34.png` |
| UX-9 | Theme: outline/onSurfaceVariant = navy, outlineVariant = navy 40%; màn quyền: câu "HỏiCon chỉ biết tên ứng dụng vừa mở…", nhãn "Mở cài đặt cho mục …", mục đã bật ẩn nút; "như một người gác cổng" | build + lint |
| SEC-1 | `setHideOverlayWindows(true)` (API 31+, quyền normal `HIDE_OVERLAY_WINDOWS`); `filterTouchesWhenObscured` cho các nút; `dispatchTouchEvent` bỏ mọi chạm có `FLAG_WINDOW_IS_(PARTIALLY_)OBSCURED` và gửi CANCEL (cả View lẫn Compose), mốc `pause_obscured` | aapt2: quyền mới duy nhất là `HIDE_OVERLAY_WINDOWS`. **Chưa thử với overlay thật** (máy ảo không có app overlay bên thứ ba) |
| SEC-2 | Hành động trợ năng "Tiếp tục" (+ ACTION_LONG_CLICK) ⇒ đếm 3 giây có đọc to (bỏ đọc khi TalkBack đã đọc live region) ⇒ nút "Đúng, vẫn tiếp tục"; chạm đơn chỉ hiện hướng dẫn; ghi `continue_via=a11y` | logic trong `HoldToContinue`; **chưa thử bằng TalkBack/Switch Access** |
| SEC-4 | `HcTiming`/`HcSpikeLog` chỉ chạy khi `BuildConfig.DEBUG` (bật `buildFeatures.buildConfig`); log `cat=bank` thay tên gói | build |
| SEC-6 | `RiskEngine.mergeCall` (`:rules`): flagged OR, giữ mốc bắt đầu sớm nhất, cuộc gọi tin cậy không đóng/ghi đè cửa sổ chưa tin cậy; `HcCallScreeningService` gộp thay vì ghi đè; cuộc gọi mới chưa tin cậy xóa "đã tiếp tục" | test thuộc tính "cuộc gọi sau không bao giờ hạ mức" (mọi tổ hợp) + 4 test gộp; trên máy ảo log `merged=true window_flagged=true` |
| SEC-7 | h1 demo và công tắc `spike_compose_pause` chỉ ở bản debug (release không đọc đĩa trên đường găng) | build |
| SEC-8 | Ưu tiên engine `com.google.android.tts`; chỉ dùng Voice vi-VN có `isNetworkConnectionRequired == false` và đã cài; không có ⇒ `tts_unavailable`, im lặng | api34/29: `tts_started` mọi lần |
| SEC-9 | Trần tuyệt đối `MAX_WINDOW_MS` = **2 giờ** tính từ cuộc gọi mới nhất (không chọn 60 phút: kịch bản "công an" giữ máy nạn nhân hàng giờ) + 10 phút sau khi kết thúc; chỉ `MODE_RINGTONE`/`MODE_IN_CALL` tính là đang gọi | test trần + cửa sổ |
| SEC-10 | `PhoneHasher` bỏ `\p{Z}` và `\p{Cf}`; thêm 3 vector (NBSP, LRE/PDF, LRM) vào `gen_h1_vectors.mjs`, sinh lại `h1_vectors.json` (19 vector) | `PhoneHasherTest` + `PhoneHasherVectorsTest` + backend `test_h1_vectors.py` (3 passed) |
| SEC-12 | `AiDisclosureCopyTest` (`:rules`, đọc `strings.xml` + `Notifications.kt` qua system property): câu đọc đầu và dòng công khai bắt đầu bằng "Đây là trợ lý AI HỏiCon", mỗi `Notification.Builder` có `setSubText(notif_ai_subtext)`, trợ lý không xưng con/cháu | 4 test xanh |
| GAP | `ForegroundTracker` (`:rules`, dựng lại app tiền cảnh từ RESUMED/PAUSED/STOPPED, nạp lại an toàn) + `RiskEngine.evaluateForegroundDuringCall` (cuộc gọi đã nối + app tài chính đang ở trước ⇒ R1); dịch vụ nạp 6 giờ sự kiện khi mở cửa sổ, mỗi "lượt app ở trước" chỉ nhắc 1 lần | 8 test; máy ảo `bank_first` (mở demobank → gọi → nghe, không chạm): **api34 5/5** (nối máy → E7 p50 948 / max 1 523 ms, tiến trình nguội), **api29 3/3** (p50 1 358 / max 2 023 ms, nhánh `PhoneStateListener`) |

**Hồi quy (api34, ấm, n=10):** 10/10, phát hiện p50 405 / p95 904 ms, mở p50 240 / p95 640 ms, SafePause p50 815 /
p95 1 056 ms ⇒ đạt ≤ 3 s. Tải máy ảo lúc đo thấp hơn lượt đầu (load ~3) nên không quy toàn bộ cải thiện cho code.
`:rules:test` **51/51** (AiDisclosureCopy 4, PhoneHasher 9, PhoneHasherVectors 3, RiskEngine 17, RiskLevel 2,
RiskWindowRules 13, SchemaContract 3 — chưa tính test của phiên chính nếu có thêm), `:app:assembleDebug` + `:app:lintDebug`
xanh (0 lỗi, 7 cảnh báo cũ/nhỏ).

**Còn tồn sau lượt này:** ở cỡ chữ 200% trên màn 360×640 dp, vùng cuộn chỉ đủ cho dòng công khai AI + "Nghe lại";
tiêu đề phải cuộn mới thấy (giọng đọc vẫn nói đủ) ⇒ P2-05 cân nhắc bố cục gọn khi chiều cao còn lại < ~300 dp.

## Việc còn lại (hoãn có chủ đích — không làm trong P1-S1)
- **SEC-3** đồng ý + công bố nổi bật cho từng quyền nhạy cảm (P2-02, màn E3).
- **SEC-5** Room + Tink thay SharedPreferences cho trạng thái cửa sổ rủi ro (P2-05, DATA-MODEL §5).
- Nút **"Hỏi con"** thật (thông báo người giám hộ, E9) thay cho mở trình quay số (P2-06).
- Biến thể **diễn tập** của E7 và thông báo (`is_drill`, màu riêng) (P2-13).
- **buildType demo + R8** (bản cài cho gian/thí điểm, đo lại khởi động nguội và hạn sàng lọc 5 s) (P1-08).
- Thử TalkBack/Switch Access cho đường SEC-2, overlay thật cho SEC-1, bộ rung thật cho UX-6 — cần máy vật lý.
