# Spike P1-S2: Dừng an toàn khi người dùng mở app ngân hàng

- Thời gian: 14/10/2026 (bắt đầu sớm so với lịch 20–28/10) · Nhánh `feat/p1-s2-safe-pause-bank` · Liên quan: ADR-007,
  **ADR-008** (quyết định rút ra từ spike này), `docs/spikes/P1-S1-cam-bien.md`
- Sản phẩm phải có theo ROADMAP: **bảng kết quả** + `data/bank_apps.vn.json` **v1**.
- Kết luận ngắn:
  - App ngân hàng thật **không thể** thử trên máy ảo hay Firebase Test Lab (FTL), vì luật bắt chúng tự dừng.
  - Mục tiêu thử và demo là `:demobank`.
  - Độ trễ trên máy thật sẽ đo bằng bộ đo `:latency` trên FTL (đã sẵn sàng, chờ tài khoản Firebase P0-08).
  - Full-screen intent không đem lại gì khi máy đang mở khóa ⇒ không dùng ở bản phát hành.
  - Phản ứng của app ngân hàng thật được ghi vào **sổ rủi ro** (§4), kèm giao thức thử trên máy thật (§5): trên máy của
    chính thành viên đội ngay sau P1-08; trên máy mượn chỉ sau P1-08 **và** P2-02, P2-05 (mục "Chặn phát hành").

## 1. Căn cứ (tra cứu ngày 14/10/2026)

| Sự kiện | Nguồn | Hệ quả |
|---|---|---|
| **Thông tư 77/2025/TT-NHNN** (theo nguồn thứ cấp, chưa đối chiếu Công báo; sửa Thông tư 50/2024; Điều 5 sửa Điều 8, hiệu lực **01/3/2026**): app Mobile Banking phải tự thoát/dừng và hiển thị lý do khi phát hiện **trình gỡ lỗi, máy ảo/giả lập, chế độ ADB**; code tiêm vào lúc chạy (hooking); app bị sửa/đóng gói lại. Đi kèm: thiết bị root/jailbreak/mở khóa bootloader | Bài thứ cấp, nội dung thống nhất với nhau: [antoanthongtin.vn](https://antoanthongtin.vn/tin/tu-thang-3-2026-quy-dinh-ve-an-toan-bao-mat-cho-viec-cung-cap-dich-vu-truc-tuyen-trong-nganh-ngan-hang-co-hieu-luc), [luatvietnam.vn](https://luatvietnam.vn/linh-vuc-khac/diem-moi-thong-tu-77-2025-tt-nhnn-ve-bao-mat-online-banking-883-106480-article.html), [thuvienphapluat.vn](https://thuvienphapluat.vn/phap-luat/tu-132026-cac-thiet-bi-nao-khong-chay-duoc-app-ngan-hang-theo-thong-tu-77-sua-doi-thong-tu-50-251118.html). **Chưa đối chiếu được văn bản gốc trên Công báo** | Không chạy được app ngân hàng thật trên máy ảo hay FTL (máy FTL luôn bật ADB). Máy thật dùng để thử phải **tắt** chế độ nhà phát triển và gỡ lỗi USB ⇒ phải cài HỏiCon qua Play |
| Báo chí nêu thêm "cài ứng dụng từ nguồn không chính thống" là dấu hiệu rủi ro | [thegioididong.com](https://www.thegioididong.com/tin-tuc/tu-1-3-mot-loat-smartphone-khong-the-dung-duoc-ung-dung-ngan-hang-1590295), [cafef.vn](https://cafef.vn/ngan-hang-tang-bao-mat-tren-thiet-bi-nguoi-dung-188260309092255685.chn) | Coi là rủi ro (chưa thấy trong văn bản gốc): chỉ phân phối HỏiCon qua Play (ADR-005, ADR-008) |
| VPBank NEO (từ bản 5.11.2, năm 2023) **chặn đăng nhập** khi có app rủi ro đang bật **quyền trợ năng**; nhiều ngân hàng khuyến cáo tương tự | [lsvn.vn](https://lsvn.vn/vpbank-canh-bao-thu-doan-lua-dao-chiem-doat-quyen-dieu-khien-dien-thoai-android-1702032019-a138512.html) | HỏiCon **không** dùng trợ năng (CLAUDE.md luật 3). Chưa có nguồn công khai nào nói app ngân hàng chặn quyền "hiển thị trên ứng dụng khác" ⇒ rủi ro RB-2, phải thử trên máy thật |
| Full-screen intent (FSI): máy **đang khóa** ⇒ hiện activity toàn màn hình; máy **đang mở khóa** ⇒ chỉ hiện thông báo mở rộng (heads-up). App target Android 14+: Play **chỉ cấp `USE_FULL_SCREEN_INTENT` cho app gọi điện/báo thức**, thu hồi quyền mặc định của các app khác; kiểm bằng `NotificationManager.canUseFullScreenIntent()` | `kb://android/develop/ui/compose/notifications/create-notification`, `kb://android/about/versions/14/behavior-changes-14` | R1 chỉ kích hoạt khi app ngân hàng đang ở tiền cảnh, tức máy đang mở khóa ⇒ FSI chỉ cho ra heads-up, trùng với đường dự phòng đã có (ADR-007). Ngoài ra HỏiCon là app sàng lọc cuộc gọi, không phải app gọi điện ⇒ khai báo FSI dễ bị Play từ chối |

## 2. Danh sách app tài chính v1 (`data/bank_apps.vn.json`, `2026.10.14-v1`)

- **50 gói**: 38 ngân hàng (gồm `vn.hoicon.demobank`, gắn `demo: true`), 7 ví điện tử, 5 chứng khoán. Chỉ khớp **đúng
  tên gói** (`com.vnpay.*` dùng chung cho nhiều ngân hàng và một ví). 6 ứng viên bị loại có ghi lý do (`unverified`).
  Techcombank OneU **chốt không đưa vào**: app tích điểm, mở hằng ngày ⇒ báo nhầm cao, không chuyển tiền cho người khác.
- **Một nguồn sự thật**: `python scripts/gen-bank-apps.py` sinh ra `rules/BankAppCatalog.kt` (thay `BankApps.kt` cũ,
  vốn chỉ có 9 gói viết tay) và khối `<queries>` trong `AndroidManifest.xml` (đủ 50 gói, vẫn **không** dùng
  `QUERY_ALL_PACKAGES`).
- **Chống lệch**: `BankAppCatalogTest` (3 test: JSON = catalog, JSON = `<queries>`, chỉ khớp đúng tên và phân biệt
  hoa/thường) chạy trong `:rules:test` trên CI. Backend kiểm schema `docs/schemas/bank_apps.v1.json` (đã có từ P1-S1).
- Việc còn lại: tải bản mới qua `GET /v1/config` (P2); rà soát mỗi quý (cùng nhịp "≥ 3 tháng rà soát phiên bản" mà
  Thông tư 77 đặt cho ngân hàng — app mới như LPBank Plus, MSB Digital Bank xuất hiện thường xuyên).

## 3. Bảng kết quả

| # | Hạng mục | Kết quả | Bằng chứng | Trạng thái |
|---|---|---|---|---|
| 1 | `data/bank_apps.vn.json` v1 + sinh mã + `<queries>` | 50 gói; catalog và manifest khớp JSON | `:rules:test` **54/54** (thêm `BankAppCatalogTest` 3), `:app:assembleDebug` xanh | ✅ |
| 2 | `:demobank` mô phỏng ngân hàng | Luồng đăng nhập → trang chủ → chuyển tiền (điền sẵn kịch bản "tài khoản tạm giữ" hư cấu) → kiểm tra lại → Smart OTP (mô phỏng, có câu "ngân hàng thật không bao giờ hỏi mã này") → kết quả. Không mạng, không quyền. Extra `screen=transfer` (mở thẳng form, dùng cho kịch bản), `secure=true` (`FLAG_SECURE` như app thật; mặc định tắt để quay video được). Trạng thái form còn nguyên sau khi đi qua SafePause rồi quay lại (`rememberSaveable`) | build xanh; **chưa chụp màn hình** (máy ảo chưa chạy, xem §6) | ◐ chờ ảnh + `ux-elder-reviewer` |
| 3 | App ngân hàng thật trên máy ảo / FTL | **Suy ra là không khả thi** (chưa thử — và không nên thử): app phải tự dừng khi có máy ảo/ADB (TT 77 Điều 5, theo nguồn thứ cấp) | §1 | ✅ kết luận ⇒ sổ rủi ro §4 + giao thức máy thật §5 |
| 4 | Full-screen intent, Android 14+ | Theo tài liệu: mở khóa ⇒ heads-up; Play giới hạn quyền. Đã gắn FSI vào thông báo dự phòng, **chỉ ở bản debug** (manifest `src/debug`), ghi log `fsi=`; CI kiểm manifest release không có quyền này | merged manifest: debug có `USE_FULL_SCREEN_INTENT` + `ScenarioReceiver`, release không có | ◐ chờ đo trên AVD API 34/36 (chỉ để xác nhận tài liệu) |
| 5 | Độ trễ trên máy thật (mở từ ADR-007) | Bộ đo `:latency` (test instrumentation tự chạy, kiểu Macrobenchmark): mô phỏng cuộc gọi bằng `ScenarioReceiver` (chỉ debug; quyền `DUMP` ⇒ chỉ shell/adb, root hoặc app hệ thống gửi được) ⇒ mở `:demobank` ⇒ đo `app_foreground → pause_shown`, 10 lần nguội + 10 lần ấm, xuất `latency.json` + logcat `HC_LATENCY`. Script: `bash scripts/ftl-latency.sh model=…,version=…` | build xanh | ◐ chờ Firebase (P0-08), rồi chạy trên ≥ 2 máy thật trước G1 |

## 4. Sổ rủi ro: HỏiCon chạy cạnh app ngân hàng thật

Khả năng / Ảnh hưởng: C = cao, TB = trung bình, T = thấp.

| ID | Rủi ro | Khả năng | Ảnh hưởng | Giảm thiểu | Kiểm bằng |
|---|---|---|---|---|---|
| RB-1 | App ngân hàng dừng khi máy bật ADB/gỡ lỗi USB, máy ảo, root (TT 77) — nếu ai đó hướng dẫn gia đình "bật chế độ nhà phát triển để cài HỏiCon", **app ngân hàng của người già ngừng chạy** | C | C | Chỉ phát hành qua Play (internal/closed testing); tài liệu thí điểm **cấm** bước bật nhà phát triển; không bao giờ gửi APK | Giao thức §5 bước 0 |
| RB-2 | App ngân hàng (thư viện RASP) cảnh báo hoặc chặn khi có app giữ quyền "hiển thị trên ứng dụng khác" (SAW) hay quyền truy cập dữ liệu sử dụng | chưa rõ (chưa có nguồn công khai) | C | Nếu một app phổ biến chặn: cho SAW thành **tùy chọn** và người dùng app đó đi đường không cần SAW (heads-up + TTS, đã đo 1,8–2,5 s trên máy ảo); gửi thư cho ngân hàng xin vào danh sách cho phép (gắn với LOI) | §5 bước 2 với 10 app |
| RB-3 | Cài từ nguồn không chính thống bị coi là rủi ro | TB | C | Như RB-1. Bản debug chỉ dùng trên máy ảo/máy dev (đã ghi ở mục "Chặn phát hành" trong ROADMAP) | — |
| RB-4 | App ngân hàng đăng xuất hoặc hủy giao dịch khi SafePause che nó (`onStop`) | C | T (thậm chí có lợi: thêm một nhịp dừng) | E7 không hứa "quay lại đúng chỗ"; câu chữ P2-05 ghi "có thể cần đăng nhập lại" | §5 bước 3 |
| RB-5 | `FLAG_SECURE` ⇒ không chụp hay quay được màn app thật cho video/diễn tập | C | T | Video và gian trưng bày dùng `:demobank` (`secure=false`); không quay app thật | — |
| RB-6 | App chạy dạng "ứng dụng kép" hoặc "không gian thứ hai" (Xiaomi/HyperOS, user 999) ⇒ UsageStats của người dùng chính không thấy ⇒ **lọt R1** | TB | TB | Ghi giới hạn; bảng hỏi thí điểm hỏi có dùng ứng dụng kép không; thử trên máy Xiaomi thật | §5 bước 4 (nếu có máy Xiaomi) |
| RB-7 | Chuyển tiền qua app Smart OTP riêng hoặc qua trình duyệt (internet banking) ⇒ không nằm trong danh mục | TB | TB | R1 bao 50 app chính. App OTP riêng: xem xét cho v2 (ghi ROADMAP). Trình duyệt: không đưa vào (báo nhầm rất cao) | — |
| RB-8 | Ngân hàng đổi gói hoặc ra app mới ⇒ danh mục lỗi thời | C | TB | Rà soát hằng quý; `GET /v1/config` (P2); test chống lệch giữ app và JSON khớp nhau | lịch rà soát |
| RB-9 | SafePause bật lên đúng lúc app ngân hàng đang hiện `BiometricPrompt` | T | T | Prompt thuộc task ngân hàng, SafePause (task riêng) nằm trên; app ngân hàng hủy xác thực khi `onPause` | §5 bước 3 |

## 5. Giao thức thử trên máy thật với app ngân hàng thật

**Khi nào được chạy** (review bảo mật 14/10, mục "Chặn phát hành" của ROADMAP): HỏiCon thấy **mọi** cuộc gọi đến của
chủ máy (kể cả của người thứ ba); bản hiện tại chưa có công bố nổi bật/bản ghi đồng ý (P2-02), chưa mã hóa trạng thái
(P2-05) ⇒
- sau P1-08 (Play internal testing): chỉ trên máy **của chính thành viên đội** (coi như máy dev);
- trên máy mượn: chỉ sau P1-08 **và** P2-02, P2-05, kèm mẫu đồng ý giấy có số phiên bản (mục đích, dữ liệu, thời hạn,
  cách rút đồng ý, việc quay video ở bước 3).

Điều kiện: chủ máy ≥ 18 tuổi, đã đồng ý bằng văn bản, tự đăng nhập ngân hàng. **Không chuyển tiền thật, không nhập
OTP**: dừng ở màn chuyển tiền. Không chụp số dư hay số tài khoản (nếu cần chụp thì chỉ chụp phần cảnh báo). Không ghi
tên chủ máy. App được chọn: VCB Digibank, BIDV SmartBanking, VietinBank iPay, Agribank Plus, MB Bank,
Techcombank Mobile, VPBank NEO, ACB ONE, MoMo, Zalopay.

0. HỏiCon cài **từ Play internal testing**; *Cài đặt → Tùy chọn nhà phát triển* **tắt**; gỡ lỗi USB tắt. Ghi lại app
   đang giữ vai trò "ID người gọi & spam" (*Ứng dụng mặc định*): cấp vai trò cho HỏiCon sẽ thay app đó.
1. Mở từng app ngân hàng **trước** khi cấp quyền nào cho HỏiCon ⇒ ghi mốc chuẩn (app có cảnh báo gì không).
2. Cấp lần lượt 5 quyền (vai trò sàng lọc → hiển thị trên ứng dụng khác → dữ liệu sử dụng → thông báo → không giới hạn
   pin). Sau **mỗi** quyền, mở lại app ngân hàng ⇒ ghi: bình thường / cảnh báo (chép nguyên văn) / từ chối chạy.
3. Một thành viên đội gọi từ số **không có trong danh bạ** ⇒ nghe ⇒ mở app ngân hàng ⇒ ghi: SafePause có hiện không,
   thời gian (quay bằng máy thứ hai rồi đếm khung hình), sau "Vẫn tiếp tục" app ngân hàng còn ở màn đang dở hay bắt
   đăng nhập lại. Trước khi quay: chủ máy bật "ẩn số dư" trong app ngân hàng; máy quay **tắt đồng bộ đám mây** (hoặc
   bật chế độ máy bay); xóa video trong 24 giờ sau khi đếm khung hình. §7 chỉ ghi con số.
4. (Máy Xiaomi/HyperOS) lặp bước 3 với app ngân hàng chạy ở chế độ "ứng dụng kép".
5. Gỡ HỏiCon ⇒ app ngân hàng chạy lại bình thường? Trả vai trò "ID người gọi & spam" cho app đã ghi ở bước 0 (gỡ app
   không tự trả lại) và kiểm tra. Ghi kết quả vào §7.

## 6. Việc còn chờ (không đo được hôm nay)

- **Máy ảo chưa chạy**: máy dev chỉ còn ~0,5 GB RAM trống, ổ C còn 0,9 GB; Minh chưa đồng ý dừng stack khác. Lint
  cục bộ cũng bị sập daemon (JVM hết bộ nhớ cam kết) ⇒ lint chạy trên CI (đã thêm `:app:lintDebug :demobank:lintDebug`).
  Khi có RAM: (a) ảnh `:demobank` ở cỡ chữ 100% và 200% ⇒ `ux-elder-reviewer`; (b) `./gradlew :latency:connectedDebugAndroidTest`
  trên `hc-api36` và `hc-api34` để kiểm bộ đo; (c) FSI: thu hồi SAW (`appops set … SYSTEM_ALERT_WINDOW deny`) ⇒ mở
  demobank trong cửa sổ rủi ro ⇒ ghi heads-up hay activity và giá trị `fsi=` trong log.
- **FTL**: cần tài khoản Firebase (P0-08). Spark cho 5 lượt máy thật/ngày ⇒ lượt đầu chọn 1 Samsung dòng A (Android 14)
  và 1 Pixel (Android 15/16).
- **Máy thật + app ngân hàng thật**: sau P1-08 (Play internal testing), theo §5.

## 7. Kết quả máy thật

| Ngày | Máy (model, Android) | Nguồn | Hạng mục | Kết quả |
|---|---|---|---|---|
| _chờ_ | FTL ×2 | máy thật · bản debug · cuộc gọi mô phỏng · demobank | `:latency` nguội/ấm n=10 | |
| _chờ_ | máy thành viên đội (sau P1-08); máy mượn (sau P2-02, P2-05) | máy thật | §5 với 10 app | |
