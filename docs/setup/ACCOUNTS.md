# Tài khoản & khóa dịch vụ cho HỏiCon (P0-08)

> Dành cho Minh — các bước **chỉ chủ tài khoản làm được** (danh tính, thanh toán, đăng nhập). Claude đã làm sẵn phần
> trên máy: `gh` đăng nhập, `cloudflared` cài, repo + PR khởi tạo, và hai lệnh:
> - `uv run --directory backend python -m hoicon.ops.init_env` — **Minh chạy một lần**: tạo `backend/.env`, tự sinh
>   pepper băm số điện thoại + bí mật webhook Zalo (không in ra), để sẵn chỗ trống cho 3 khóa dán tay.
> - `uv run --directory backend python -m hoicon.ops.check_keys` — kiểm tra từng khóa bằng lời gọi chỉ-đọc miễn phí,
>   chỉ in Đạt/Thiếu/Lỗi. Claude chạy được lệnh này để xác nhận mà không thấy khóa.
> Tra cứu ngày 08/10/2026; điều khoản các nền tảng có thể đổi.

## Thứ tự ưu tiên

| # | Tài khoản | Làm khi nào | Cần cho task | Chi phí | Thời gian chờ |
|---|---|---|---|---|---|
| 1 | **Google Play Console** (cá nhân) | **Ngay hôm nay** | P1-08, P2-14, thí điểm | 25 USD một lần | Xác minh danh tính: vài ngày |
| 2 | GitHub Student Developer Pack | Ngay | P1-09 (VPS, tên miền miễn phí) | 0 | vài ngày duyệt |
| 3 | Zalo Bot Platform (bot dev) | trước 22/10 | P1-S3 | 0 (3 bot × 50 người × 3.000 tin/tháng) | tức thì |
| 4 | Anthropic API (Claude Console) | trước 26/10 | P1-S4, P2 | trả trước, đề xuất 10–20 USD | tức thì |
| 5 | Gemini API (Google AI Studio) | trước 26/10 | P1-S4/S5 | free tier (chỉ dữ liệu giả) | tức thì |
| 6 | Firebase (Spark, miễn phí) | trước 15/10 | P1-S1/S2 (Test Lab, Device Streaming), P2-08 (FCM) | 0 | tức thì |
| — | GitHub, cloudflared | **xong** (Claude làm 08/10) | P0-07, P1-S3 | 0 | — |

**Bảo mật chung (repo này PUBLIC):** bật xác minh 2 bước cho mọi tài khoản. **Không dán khóa vào khung chat với
Claude**, issue hay PR — mở `backend/.env` bằng VS Code và dán trực tiếp (Claude bị chặn đọc file này). Sao lưu pepper
và keystore ở `D:\secrets\` (ngoài repo). Khóa quyền: `icacls backend\.env /inheritance:r /grant:r "%USERNAME%:F"`
(mặc định ổ D: cho `Everyone` toàn quyền). Lưới an toàn: workflow `secrets` (gitleaks) chạy trên mọi push/PR và
GitHub Secret scanning + Push protection đã bật cho repo.

---

## 1. Google Play Console — tài khoản cá nhân

**Vì sao ngay:** xác minh danh tính mất nhiều ngày; ADR-005 phát hành qua kênh thử nghiệm của Play (không phát APK cho
người cao tuổi).

**Chuẩn bị:** tài khoản Google (khuyên dùng một tài khoản riêng cho dự án, dạng `<tên-dự-án>@gmail.com` do Minh tự chọn, bật 2FA);
CCCD/hộ chiếu; địa chỉ; số điện thoại; **thẻ Visa/Mastercard** (thẻ ghi nợ quốc tế của ngân hàng VN dùng được) để trả
25 USD.

**Các bước:**
1. Vào https://play.google.com/console/signup → chọn **Yourself / Cá nhân** (tài khoản tổ chức cần số D-U-N-S và pháp
   nhân — không kịp trước 15/11).
2. Điền tên nhà phát triển công khai: **HỏiCon**; email liên hệ công khai: email dự án. Tên pháp lý được xác minh
   riêng. **Đọc kỹ màn "thông tin hiển thị trên Google Play" trước khi lưu** — app miễn phí thì **không tạo hồ sơ
   thanh toán bán hàng (merchant)**, vì tài khoản cá nhân có bán hàng phải công khai địa chỉ (chưa kiểm chứng được
   chi tiết hiển thị — xác nhận trên màn đăng ký).
3. Trả phí 25 USD → **xác minh danh tính** (tải ảnh CCCD) → chờ email duyệt.
4. Trả lời khảo sát kinh nghiệm phát triển Android (ghi trung thực: sinh viên, chưa phát hành app).

**Hai yêu cầu với tài khoản cá nhân mới (đã kiểm chứng):**
- **Xác minh có điện thoại Android thật:** trước khi đưa app lên Google Play, phải mở app *Play Console* trên **một
  điện thoại Android thật, không root, Android 10+**, đăng nhập đúng tài khoản chủ sở hữu và bấm *Verify* (< 1 phút,
  làm một lần, **máy không cần là của mình** — một máy dùng được cho nhiều tài khoản). Xem §7.
- **Kiểm thử kín 12 người × 14 ngày:** chỉ bắt buộc trước khi xin quyền phát hành **chính thức (production)**. HỏiCon
  chỉ dùng kênh **internal / closed testing** cho thí điểm ⇒ **không bị chặn** bởi yêu cầu này. (Nếu sau chung kết muốn
  lên production: closed test ≥ 12 tester liên tục 14 ngày — gia đình thí điểm đủ điều kiện.)

**Sau khi có tài khoản (P1-08, 14–22/11):** tạo app `vn.hoicon.sentinel`, bật Play App Signing, tạo Google Group
tester, kênh internal testing. Claude chuẩn bị Data safety + khai báo FGS `specialUse` (`docs/PLAY-POLICY.md`).

## 2. GitHub Student Developer Pack

https://education.github.com/pack → xác minh bằng email `@student.tdtu.edu.vn` + thẻ sinh viên. Hữu ích cho P1-09: tín
dụng VPS và tên miền miễn phí 1 năm trong gói (danh sách ưu đãi thay đổi theo thời điểm — kiểm tra khi được duyệt),
GitHub Pro (3.000 phút Actions/tháng cho repo private).

## 3. Zalo Bot Platform — bot dev

1. Mở app **Zalo** (điện thoại hoặc Zalo PC) → tìm Official Account **"Zalo Bot Manager"** → menu **Tạo bot** → mở
   *Zalo Bot Creator*.
2. Tên bot **bắt buộc bắt đầu bằng "Bot"** — đề xuất: `Bot HỏiCon Dev` (dev), sau này `Bot HỏiCon 1/2/3` cho thí điểm.
   Ảnh đại diện: logo tạm (P1-05 có logo thật).
3. Sau khi tạo, Zalo **gửi Bot Token qua tin nhắn** cho tài khoản Zalo của Minh → dán vào `backend/.env`:
   `HOICON_ZALO_BOT_TOKEN=...` rồi **xóa tin nhắn chứa token** trong Zalo (tin được đồng bộ sang Zalo PC/máy khác).
4. Bí mật webhook (8–256 ký tự) `HOICON_ZALO_WEBHOOK_SECRET` đã được `init_env` sinh sẵn — không cần làm gì.
5. Phần còn lại làm ở P1-S3 **mà không ai phải cầm token trong lệnh**: script `hoicon.ops.zalo_webhook` (theo mẫu
   `check_keys`: đọc token từ `.env`, gọi `setWebhook` với `url` + `secret_token`, chỉ in Đạt/Lỗi). Đường hầm
   `cloudflared tunnel --url …` (URL HTTPS tạm, không cần tài khoản Cloudflare) chỉ trỏ tới **app con chứa riêng route
   webhook** — không mở `/docs`, `/openapi.json`, `/mcp/*` ra Internet. Zalo gửi lại bí mật trong header
   `X-Bot-Api-Secret-Token` ở mọi webhook. Token Zalo nằm trên **đường dẫn URL** (thiết kế của Zalo) ⇒ yêu cầu bắt buộc
   cho code P1-S3 ghi ở ADR-003.

**Giới hạn miễn phí:** tối đa **3 bot**, mỗi bot **50 người dùng** và **3.000 tin/tháng** (ADR-003, bộ kiểm hạn mức
`messages_out`). Bot gắn với tài khoản Zalo cá nhân của Minh.

## 4. Anthropic API (Claude Console)

1. https://platform.claude.com (Claude Console) → đăng ký bằng email dự án → tạo Organization "HỏiCon".
2. **Billing** → nạp trước 10–20 USD (đủ cho spike và eval đầu tiên).
3. **Organization settings → Billing → Spend limits:** đặt giới hạn tháng của tổ chức (đề xuất 20 USD).
4. Tạo **Workspace** `hoicon-dev` → tab *Spend limits* đặt thấp hơn (đề xuất 15 USD). Khi chạm giới hạn, API dừng tới
   00:00 UTC ngày 1 tháng sau — không phát sinh nợ.
5. Trong workspace `hoicon-dev` → **API keys → Create key** tên `hoicon-dev-local` → dán `HOICON_ANTHROPIC_API_KEY=...`.
   (Sau này tạo workspace `hoicon-pilot` riêng cho VPS thí điểm.)

Mô hình dự kiến (`docs/AGENTS.md`): `fast` = Claude Haiku 4.5, `strong` = Claude Sonnet 5.5.

## 5. Gemini API (Google AI Studio)

1. https://aistudio.google.com → **Get API key → Create API key** → tạo Google Cloud project **riêng `hoicon-ai`**
   (KHÔNG dùng chung với Firebase: khóa Android của Firebase nằm công khai trong APK, mà khóa Google Cloud có phạm vi
   theo project ⇒ chung project thì người khác trích khóa từ APK là gọi được Gemini bằng quota/billing của Minh).
   Trong Cloud Console → *APIs & Services → Credentials*: giới hạn khóa này **chỉ cho Generative Language API**.
2. Dán `HOICON_GEMINI_API_KEY=...`.
3. **Free tier: Google có thể dùng prompt/phản hồi để cải thiện sản phẩm và người đánh giá có thể đọc** ⇒ chỉ gửi dữ
   liệu **giả lập** (eval, kịch bản). Dữ liệu thí điểm thật chỉ đi qua gói **trả phí** (bật billing) hoặc Claude
   (`docs/PRIVACY-DPIA.md`).

## 6. Firebase (gói Spark, miễn phí)

1. https://console.firebase.google.com → **Add project** → tên **`hoicon-app`** (project riêng, tách khỏi `hoicon-ai`;
   tắt Google Analytics). Sau đó trong Cloud Console giới hạn khóa Android của Firebase: chỉ các Firebase API + ràng
   buộc app Android (package + SHA-1).
2. **Add app → Android:** package `vn.hoicon.sentinel`, nickname "Lính gác". Tải `google-services.json` → đặt tại
   `apps/android/app/google-services.json` (đã gitignore; Claude bị chặn đọc). Thêm app thứ hai `vn.hoicon.demobank`
   nếu cần.
3. Dùng cho: **FCM** (P2-08), **Crashlytics** (P2-20), **Test Lab** — Spark: **5 lượt/ngày trên máy thật**, 10 lượt/ngày
   máy ảo (Test Lab ngừng hoạt động 30/09/2027 — sau chung kết, không ảnh hưởng), **Android Device Streaming** — **30
   phút miễn phí/project/tháng** trên máy thật (Pixel 9, Samsung, Xiaomi, OPPO, vivo…), vượt mức 0,15 USD/phút (Blaze).

## 7. Nghiên cứu: không có máy Android thật thì làm thế nào?

**Câu hỏi:** máy ảo có thay được máy thật không? **Trả lời ngắn:** cho **phát triển, kiểm thử, demo, quay video —
được** (đã dựng xong, `docs/EMULATOR.md`). Cho **bước xác minh thiết bị của Play Console — không**.

| Phương án | Dùng cho xác minh Play? | Ghi chú |
|---|---|---|
| Máy ảo Android Studio (AVD, kể cả ảnh Google Play) | **Không** | Google yêu cầu rõ "non-rooted **physical** Android device". Máy ảo bị nhận diện qua Play Integrity (phần cứng giả, cảm biến, IP) ⇒ không đạt; cố lách có thể bị gắn cờ tài khoản |
| **Mượn máy Android của người thân** (Android 10+) | **Có — khuyên dùng** | Cài app Play Console, đăng nhập tài khoản dev, bấm Verify (< 1 phút), rồi **Cài đặt → Tài khoản → Xóa tài khoản Google** (đăng xuất app chưa đủ; tắt đồng bộ) + gỡ app. Google cho phép dùng máy không phải của mình, một máy cho nhiều tài khoản. Máy của bố/mẹ cũng là máy thí điểm tự nhiên |
| Android Device Streaming (máy thật từ xa của Google, `android device remote`) | Về kỹ thuật có thể, **không khuyên** | Là máy vật lý, 30 phút miễn phí/tháng; nhưng phải đăng nhập tài khoản Google chủ Play Console vào máy dùng chung của trung tâm dữ liệu (dù bị xóa sạch sau phiên) — dễ kích hoạt cảnh báo bảo mật tài khoản, không được Google xác nhận cho mục đích này ⇒ rủi ro cho tài khoản Play |
| Mua máy cũ 1–2 triệu | Có | Giải quyết luôn rủi ro #2 (giới hạn nền của từng hãng). Khuyến nghị trước 06/12 (gate M2 cần ≥ 1 máy thật) |
| Liên hệ Google Support xin cách xác minh khác | Không chắc | Không có quy trình công bố |
| Tài khoản tổ chức (không cần xác minh thiết bị) | — | Cần D-U-N-S + pháp nhân, mất vài tuần |

**Thời điểm cần xác minh:** trước khi đưa bản đầu tiên lên Play (P1-08, **trước 14/11**) — Play Console hiện nhiệm vụ
"Verify that you have access to an Android mobile device" trên trang chủ. Đăng ký tài khoản **ngay** (chờ duyệt danh
tính), còn bước xác minh thiết bị làm vào lúc mượn được máy (ví dụ cuối tuần về nhà).

**Kiểm thử trên máy thật mà không cần sở hữu máy** (cho P1-S1/S2 và trước M2): Firebase Test Lab (5 lượt máy thật/ngày,
chạy test instrumentation tự động) + Android Device Streaming (30 phút/tháng điều khiển máy Samsung/Xiaomi/OPPO thật
qua `android device remote`, chỉ cài app HỏiCon — **không đăng nhập tài khoản cá nhân**). Cần `android auth login` và
project `hoicon-app` (Minh đăng nhập một lần, Claude làm phần còn lại).

**Lưu ý thêm:** chương trình *Android developer verification* (bắt buộc đăng ký nhà phát triển kể cả app cài ngoài
Play) áp dụng từ 09/2026 ở Brazil, Indonesia, Singapore, Thái Lan; mở rộng toàn cầu dự kiến 2027 — Việt Nam chưa nằm
trong đợt đầu; HỏiCon phát hành qua Play nên đằng nào cũng đáp ứng.

## 8. Nếu nghi lộ khóa

Xóa khỏi lịch sử git **không đủ** (repo public đã có thể bị sao chép) — **xoay khóa ngay**:

| Khóa | Cách xoay |
|---|---|
| Anthropic | Claude Console → API keys → *Disable/Delete* khóa cũ → tạo khóa mới → `check_keys` |
| Gemini | Cloud Console `hoicon-ai` → Credentials → *Regenerate key* / xóa khóa |
| Zalo Bot token | Zalo Bot Manager → bot → tạo lại token; chạy lại `zalo_webhook` |
| Webhook secret | xóa dòng trong `.env` → `init_env` sinh mới → chạy lại `zalo_webhook` |
| Pepper | **không xoay khi chưa có kế hoạch** — thêm `HOICON_PHONE_PEPPER_2` + `PEPPER_KID=2`, băm lại khi số xuất hiện lần sau (ADR-006) |
| GitHub token | `gh auth logout` → `gh auth login --web` (hoặc fine-grained PAT chỉ cho repo này) |

## Nguồn
- Play Console — device verification: https://support.google.com/googleplay/android-developer/answer/14316361
- Play Console — testing requirements for new personal accounts: https://support.google.com/googleplay/android-developer/answer/14151465
- Android developer verification: https://android-developers.googleblog.com/2026/03/android-developer-verification-rolling-out-to-all-developers.html
- Zalo Bot: https://docs.zaloplatforms.com/docs/BOT · https://bot.zapps.me/docs/apis/setWebhook/
- Claude Console spend limits: https://platform.claude.com/docs/en/api/admin/spend_limits/create.md
- Gemini API billing / free tier: https://ai.google.dev/gemini-api/docs/billing
- Firebase Test Lab & Device Streaming quotas: https://firebase.google.com/docs/test-lab/usage-quotas-pricing
- Android Device Streaming: https://developer.android.com/studio/run/android-device-streaming · `android device remote`: https://developer.android.com/tools/agents/android-cli/commands/device_remote
