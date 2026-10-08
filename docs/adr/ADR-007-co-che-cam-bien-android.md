# ADR-007: Cơ chế cảm biến Android của "Lính gác"

- Trạng thái: **Chấp nhận** (cơ chế) · độ trễ p95 **chờ số máy thật** · 09/10/2026
- Bằng chứng: spike P1-S1 `docs/spikes/P1-S1-cam-bien.md` (đo trên máy ảo API 36/34/29, 08/10/2026)
- Liên quan: ADR-001 (luật tất định trên máy), ADR-006 (băm số), `docs/PLAY-POLICY.md`

## Bối cảnh
ADR-001 chốt nguyên tắc (luật tất định, offline, không quyền nhạy cảm) nhưng chưa chốt **API nào** thực hiện từng mắt
xích. Android 12–16 siết dần việc khởi động foreground service (FGS) và activity từ nền; mỗi lựa chọn sai làm mất bảo
vệ đúng lúc cần. Spike P1-S1 đã kiểm 6 giả thuyết trên 3 mức API.

## Quyết định

| Mắt xích | Cơ chế chốt | Quyền / điều kiện | Bằng chứng (máy ảo) |
|---|---|---|---|
| Biết có **số lạ** gọi | `CallScreeningService` (vai trò `CALL_SCREENING`), **chỉ quan sát**, luôn cho cuộc gọi đi qua. Hệ thống chỉ gọi `onScreenCall` cho số **không có trong danh bạ** | vai trò do người dùng cấp | 10/10 cả khi app sống / bị kill / force-stop (api36, api34); 5/5 api29 |
| **Trạng thái cuộc gọi** | `AudioManager.mode` (API 31+ `OnModeChangedListener`; API 29–30 quét 1 s, kèm `PhoneStateListener` không quyền) | **không cần quyền** — **bỏ `READ_PHONE_STATE`** | 11/11 chuyển trạng thái; trễ hơn TelephonyCallback 0,1–4,3 s, không đáng kể với cửa sổ 10 phút |
| **Cửa sổ rủi ro** ≤ 10 phút | FGS `specialUse` mở từ `onScreenCall`, thông báo "HỏiCon đang bảo vệ" | **Android 15+: bắt buộc người dùng tắt tối ưu pin** cho HỏiCon (SAW một mình không đủ khi target ≥ 35); Android 14: SAW đủ | api36: chỉ SAW ⇒ FGS **0/5** (`DENIED`); SAW + tắt tối ưu pin ⇒ **5/5**; api34: SAW ⇒ 5/5 |
| **Phát hiện** app tài chính | `UsageStatsManager.queryEvents` mỗi 1 s trong cửa sổ; khớp **đúng tên gói** với `data/bank_apps.vn.json` (bank / wallet / securities); `<queries>` theo gói | usage access (người dùng cấp) | phát hiện p50 0,5–0,9 s |
| **Dừng an toàn** | `startActivity(SafePauseActivity)` trực tiếp từ FGS (miễn trừ BAL nhờ `SYSTEM_ALERT_WINDOW`), task riêng — **không vẽ overlay** lên app ngân hàng; TTS tiếng Việt khởi động sẵn khi mở cửa sổ | SAW (người dùng cấp) | mở từ nền luôn được phép khi có SAW |
| **Dự phòng** khi SafePause không hiện | watchdog 1,5 s ⇒ thông báo heads-up + câu nói TTS | thông báo | không SAW ⇒ `BAL_BLOCK` ⇒ heads-up 2,5 s, TTS 3,0 s |

Quyền khai báo của `:app` (APK, kiểm bằng `aapt2`): `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_SPECIAL_USE`,
`POST_NOTIFICATIONS`, `SYSTEM_ALERT_WINDOW`, `PACKAGE_USAGE_STATS` (+ quyền nội bộ androidx). **Không có `INTERNET`**
trong đường găng (bản spike) — đường găng không thể dùng mạng.

## Hệ quả
- **Onboarding E3** phải có 5 bước, mỗi bước một màn, có hình minh họa và ghi đồng ý: vai trò sàng lọc cuộc gọi →
  hiển thị trên ứng dụng khác → truy cập dữ liệu sử dụng → thông báo → **"Không giới hạn pin"** (mở màn danh sách cài
  đặt pin; **không** dùng quyền `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` — Play hạn chế quyền này).
- **Heartbeat** gửi trạng thái từng điều kiện (vai trò, SAW, usage access, thông báo, miễn tối ưu pin) ⇒ báo người
  giám hộ khi "mất bảo vệ".
- Khởi động app phải **nhẹ** (Telecom chỉ chờ sàng lọc ~5 s): không `Application` nặng, bật R8 + baseline profile ở
  bản phát hành.
- Thông báo cửa sổ rủi ro dùng kênh `IMPORTANCE_DEFAULT` **tắt âm thanh/rung** (`protecting_v2`) để có biểu tượng trên
  thanh trạng thái (kênh `IMPORTANCE_LOW` bị gom vào "Silent"; `Notification.Builder` của nền tảng không có `setSilent`).
- Cửa sổ rủi ro: "đang gọi" chỉ tính `MODE_RINGTONE`/`MODE_IN_CALL`; đóng 10 phút sau khi cuộc gọi kết thúc; **trần tuyệt
  đối 2 giờ** từ cuộc gọi gần nhất (kịch bản "công an" giữ máy hàng giờ; chặn trường hợp tín hiệu cuộc gọi bị kẹt).
- Nhiều cuộc gọi trong một cửa sổ được **gộp, không ghi đè** (`RiskEngine.mergeCall`): cờ "bị gắn cờ" lấy OR, giữ mốc
  bắt đầu sớm nhất, cuộc gọi tin cậy không đóng cửa sổ chưa tin cậy ⇒ cuộc gọi sau không bao giờ hạ mức.
- App tài chính **mở sẵn trước cuộc gọi** (nghe máy bằng heads-up, không rời app) vẫn kích hoạt R1 khi cuộc gọi nối
  (`evaluateForegroundDuringCall`) — đã đo: api34 5/5, api29 3/3.
- SafePause chống lớp phủ: `setHideOverlayWindows(true)` (quyền thường `HIDE_OVERLAY_WINDOWS`), bỏ mọi chạm bị che
  (`FLAG_WINDOW_IS_(PARTIALLY_)OBSCURED`); người dùng trợ năng có đường "tiếp tục" riêng có xác nhận (không bỏ qua 1 chạm).
- Màn E7: chọn View thuần hay Compose **sau khi đo nguội trên máy thật** (A/B trên máy ảo: View nhanh hơn ~0,8 s ở trung
  vị). Bố cục phải giữ 2 nút trong màn đầu ở cỡ chữ 200% và màn 720×1280.

## Chưa chốt — điều kiện để đóng gate P1-S1
- **p95 phát hiện → SafePause ≤ 3 s chưa đạt trên máy ảo** (p95 5–10 s ở lô n=10; p50 ấm 1,0–1,5 s, nguội 1,7–4,2 s)
  trong khi đối chứng mở một app tầm thường trên cùng máy ảo mất 4–6 s ⇒ môi trường thổi phồng độ trễ, **không dùng số
  này để kết luận**. Phải đo lại trên **máy vật lý** (Firebase Test Lab — test instrumentation, hoặc máy mượn/mua) trước
  G1 (08/11). Nếu máy thật vẫn trượt: làm ấm UI SafePause khi mở cửa sổ rủi ro, chọn View thuần, quét 500 ms.
- Ứng viên dự phòng chưa thử: `ACTION_POST_CALL` (Telecom gửi tới app sàng lọc sau cuộc gọi).
- Chưa kiểm: TalkBack với thao tác giữ 3 s; âm thanh TTS trong lúc đang gọi; diệt tác vụ nền của từng hãng (máy ảo
  không tái hiện được — không tuyên bố tương thích hãng nào).

## Phương án đã loại
- `READ_PHONE_STATE` + `TelephonyCallback`: chính xác hơn vài trăm ms nhưng thêm quyền nguy hiểm và khai báo Play,
  không cần cho cửa sổ 10 phút.
- Chỉ dựa vào SAW để mở FGS từ nền: hỏng trên Android 15+/16 (đã đo).
- Overlay vẽ đè lên app ngân hàng: vi phạm cam kết ADR-001, rủi ro chính sách Play.
- Accessibility để biết app tiền cảnh: bị cấm (CLAUDE.md luật 3).
