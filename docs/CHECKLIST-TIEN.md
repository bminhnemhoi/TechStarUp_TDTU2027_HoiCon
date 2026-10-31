# Checklist việc của Tiến (làm một mình) — Claude tick khi Tiến báo xong

Cách dùng: làm theo thứ tự mã **H-01 → H-24**. Xong mục nào, gõ cho Claude đúng câu ở dòng **"Báo Claude"** — Claude sẽ kiểm, chạy phần
máy đi kèm, rồi đổi `- [ ]` thành `- [x]` kèm ngày. Mục nào kẹt: gõ "H-xx kẹt ở bước n: <mô tả>" để Claude gỡ.

Quy tắc chung (đọc một lần):
- **Không dán khóa, token, mật khẩu vào chat** với Claude, issue hay PR (repo public). Mở tệp bằng editor rồi dán thẳng:
  dev → `backend/.env`; VPS → `infra/.env.prod`. Claude bị chặn đọc hai tệp này — chỉ kiểm bằng lệnh in "Đạt/Thiếu <tên biến>".
- Mọi số điện thoại, tên trong demo/video phải **hư cấu**. Dữ liệu người thật chỉ có trong thí điểm (≥ 18 tuổi, có đồng ý).
- Lệnh kiểm khóa dev dùng nhiều lần: `uv run --directory backend python -m hoicon.ops.check_keys` (in Đạt/Lỗi từng khóa, không in giá trị).
- Tổng quan và lý do: `docs/HUONG-DAN-TIEN.md`. Hạn: **nộp Vòng 1 13/11/2026** · nộp Vòng 2 09/01/2027.

---

## Giai đoạn 1 — tuần này (25/10–01/11)

### - [ ] H-01 · Hỏi BTC đội 1 người có được không (5 phút)
1. Mở email hướng dẫn của BTC (hoặc trang cuộc thi) lấy địa chỉ liên hệ.
2. Gửi: "Đội em hiện có 1 thành viên là sinh viên Khoa CNTT TDTU. Theo thể lệ (nhóm không quá 05 sinh viên, > 20% sinh viên CNTT), đội 1 người
   có hợp lệ không ạ?"
3. Nếu BTC yêu cầu ≥ 2 người: rủ 1 bạn (marketing/tài chính) trước 08/11, xin họ tên + MSSV + khoa.
- **Gỡ chặn:** câu chữ đội ngũ trong thuyết minh (H-09).
- **Báo Claude:** `H-01 xong: BTC trả lời <được / cần ≥ n người>; đội gồm <tên, vai trò>.`

### - [ ] H-02 · Khóa Anthropic API có trần chi tiêu (20 phút, 10–20 USD)
1. Vào https://platform.claude.com → đăng ký bằng email dự án → tạo Organization "HỏiCon".
2. **Billing** → nạp trước 10–20 USD.
3. **Organization settings → Billing → Spend limits** → đặt 20 USD/tháng.
4. Tạo **Workspace** `hoicon-dev` → tab *Spend limits* đặt 15 USD.
5. Trong `hoicon-dev` → **API keys → Create key** tên `hoicon-dev-local` → mở `backend/.env`, thêm dòng `HOICON_ANTHROPIC_API_KEY=...`.
6. Kiểm: `uv run --directory backend python -m hoicon.ops.check_keys` → dòng Anthropic **Đạt**.
- **Gỡ chặn:** số eval với mô hình thật (Gate M3, 036), so mô hình (P1-S4), câu hỏi E8/tóm tắt do LLM thật.
- **Báo Claude:** `H-02 xong: đã có khóa Anthropic trong backend/.env, check_keys Đạt.`
  ⇒ Claude ghi cassette `recorded` cho bộ eval và đo recall/báo nhầm thật.

### - [ ] H-03 · Bot Zalo dev (15 phút, miễn phí)
1. Mở **Zalo** → tìm OA **"Zalo Bot Manager"** → menu **Tạo bot** → *Zalo Bot Creator*.
2. Tên bot **phải bắt đầu bằng "Bot"**: `Bot HỏiCon Dev`. Ảnh đại diện tạm.
3. Zalo gửi **Bot Token** qua tin nhắn → mở `backend/.env`, thêm `HOICON_ZALO_BOT_TOKEN=...` → **xóa tin nhắn chứa token** trong Zalo.
4. Nếu `backend/.env` chưa có `HOICON_DATA_KEY_1`: chạy **một lần** `uv run --directory backend python -m hoicon.ops.init_env --new-data-key`.
5. Kiểm: `check_keys` → Zalo **Đạt**.
- **Gỡ chặn:** 002 T024/T025 (đo giao tin Zalo thật p95 ≤ 5 s), cảnh Zalo thật trong video.
- **Báo Claude:** `H-03 xong: có token bot Zalo dev, check_keys Đạt.`
  ⇒ Claude dựng đường hầm cloudflared, đặt webhook, đưa bạn mã ghép để nhắn `/start <mã>`, rồi đo.

### - [ ] H-04 · Firebase (15 phút, miễn phí) — cho Test Lab đo máy thật
1. https://console.firebase.google.com → **Add project** → tên `hoicon-app` → **tắt** Google Analytics.
2. **Add app → Android**: package `vn.hoicon.sentinel`, nickname "Lính gác" → tải `google-services.json` → đặt vào
   `apps/android/app/google-services.json` (đã gitignore).
3. Cài Google Cloud CLI: `paru -S google-cloud-cli` (hoặc `yay -S`) (hoặc theo cloud.google.com/sdk) → `gcloud auth login` → `gcloud config set project hoicon-app`.
4. Kiểm: `gcloud firebase test android models list | head` in danh sách máy.
- **Gỡ chặn:** 001 T007–T010 (đo dừng an toàn trên máy thật Samsung/Pixel qua Test Lab — Spark: 5 lượt máy thật/ngày).
- **Báo Claude:** `H-04 xong: Firebase hoicon-app + gcloud đăng nhập, models list chạy được.`

### - [ ] H-05 · Tên miền + VPS đặt tại Việt Nam (1–2 giờ)
1. Đăng ký **GitHub Student Developer Pack** (education.github.com/pack) bằng email trường — chờ duyệt vài ngày; gói có tên miền miễn phí 1 năm.
2. Thuê VPS **tại Việt Nam** (thuyết minh cam kết dữ liệu trong nước): **2 vCPU, 4 GB RAM, ≥ 40 GB, Ubuntu 24.04**.
3. DNS: tạo bản ghi **A** `app.<tên-miền>` → IP VPS.
4. Trên VPS: tạo người dùng thường (không dùng root) thuộc nhóm `docker`; cài Docker Engine + Compose ≥ 2.24, `git`, `curl`, `openssl`, `uv`;
   tường lửa chỉ mở 22, 80, 443/tcp, 443/udp.
- **Gỡ chặn:** H-14 (triển khai).
- **Báo Claude:** `H-05 xong: VPS <nhà cung cấp>, Ubuntu 24.04, tên miền app.<…> đã trỏ IP.` (không gửi mật khẩu SSH)

### - [ ] H-06 · Máy Android thật (mượn/mua 1–2 triệu, trước 06/12)
1. Ưu tiên Samsung dòng A hoặc Xiaomi, Android 13–15 (người cao tuổi hay dùng). Không cần SIM mạnh, nhưng cần nghe/gọi được.
2. Bật **Tùy chọn nhà phát triển → Gỡ lỗi USB**; cắm máy, chạy `~/Android/Sdk/platform-tools/adb devices` thấy máy.
- **Gỡ chặn:** 029 T012, kiểm "cài đặt bị hạn chế" khi cài APK (H-12), M1 trên máy thật.
- **Báo Claude:** `H-06 xong: máy <hãng model>, Android <bản>, adb thấy máy.`

### - [ ] H-07 · Chốt các quyết định treo (30 phút)
Đọc bảng §3 của `docs/HUONG-DAN-TIEN.md` (17 mục + mục 18). Quyết nhanh:
1. Đồng ý hết theo đề xuất? Gõ cho Claude câu dưới. Muốn khác ở mục nào thì ghi rõ.
2. Hai mục ảnh hưởng nhiều nhất: **F-1 (mục 8)** — chọn A để Gate M3 không trượt; **mục 18** đo độ ổn định khi không có Play — chọn (a) hoặc (c).
- **Gỡ chặn:** 024 T016–T017, 011 T012, spec đồng ý người giám hộ (mục 15), task đo độ ổn định.
- **Báo Claude:** `H-07: Tiến chốt §8 theo đề xuất; mục 18 chọn <a/c>; khác: <…>.`

### - [ ] H-08 · Cài `scrcpy` + bật Orca thấy máy ảo (10 phút)
1. Gõ trong prompt Claude: `! sudo pacman -S scrcpy` (nhập mật khẩu).
2. **Đăng xuất rồi đăng nhập lại** (để nạp `~/.config/environment.d/android-sdk.conf`).
3. Mở Orca → bảng **Mobile Emulator** → chọn **hc-api36** → **Connect** (máy ảo phải đang chạy: nhờ Claude bật nếu tắt).
- **Báo Claude:** `H-08 xong: Orca hiện được máy ảo.` (hoặc chụp màn hình lỗi)

---

## Giai đoạn 2 — hồ sơ Vòng 1 (tới 13/11)

### - [ ] H-09 · Sửa thuyết minh trong Word (3–5 giờ, cần Windows + Word)
1. Mở `docs/proposal/PITCH-SYNC-2026-10-25.md` — làm lần lượt đề xuất **A → K**.
2. Mở `docs/proposal/HoiCon_Ban_mo_ta_y_tuong_TSC2027.docx` trong **Word** (KHÔNG chạy pipeline `src/` — sẽ mất các sửa tay cũ).
3. Dùng **Ctrl+H** tìm từng cụm: "50–100 gia đình", "Đội 5 người", "3/5 thành viên", "Chế độ sinh viên", "[Gọi mẹ]", "hằng tuần", "Redis",
   "Langfuse", "Gemini Live", "6.000", "Play" … rồi thay bằng câu đề xuất.
4. Viết lại **Bảng 9** theo đề xuất **G** (tác tử có ràng buộc).
5. Điền `[Điền tên đội]`, `[Họ và tên]`; xóa cố vấn chưa nhận lời.
6. Kiểm: font **Times New Roman 14**, khổ **A4**, **References → Update Table** (mục lục), không trang trắng.
7. **File → Save As → PDF**. Chép đè cả `.docx` và `.pdf` vào `docs/proposal/`.
- **Báo Claude:** `H-09 xong: đã sửa thuyết minh A–K, chép docx + pdf mới vào docs/proposal.`
  ⇒ Claude chạy `pitch-sync` kiểm "sạch" và báo chỗ còn lệch.

### - [ ] H-10 · Khảo sát ≥ 300 phản hồi (dựng 1 giờ, phát tới 06/11)
1. Mở `docs/research/survey/P1-02-bang-hoi.md` → dựng **Google Form** đúng thứ tự câu hỏi (không hỏi tên, số điện thoại).
2. Phát qua nhóm lớp, Facebook, Zalo gia đình; nhắc lại 2–3 lần.
3. **06/11**: Google Form → **Responses → tải CSV** → lưu **ngoài repo** (ví dụ `~/hoicon-private/p1-02.csv`; CSV có thể chứa dữ liệu cá nhân,
   không commit) rồi báo Claude đường dẫn.
- **Báo Claude:** `H-10 xong: n = <số> phản hồi, CSV ở <đường dẫn ngoài repo>.` ⇒ Claude lập báo cáo số liệu + câu chèn vào thuyết minh (đề xuất J).

### - [ ] H-11 · Quay video 3 phút (05–08/11, 3–4 giờ)
1. Đọc `docs/proposal/VIDEO-V1-SCRIPT.md` (phân cảnh + lời thoại + mục **"Không được nói"**).
2. Nhờ Claude chuẩn bị: `Chuẩn bị quay video: bật hc-api36 có cửa sổ, cài bản demo, backend + web, seed gia đình demo.`
3. Quay màn hình (OBS Studio: `sudo pacman -S obs-studio`) — cửa sổ máy ảo + trình duyệt `/sim`, `/trace`.
4. Thu giọng đọc (~125 từ/phút), chỗ yên tĩnh.
5. Dựng (Kdenlive hoặc nhờ Claude dùng skill `video-use`); kiểm **≤ 3:00**, có nhãn "MÔ PHỎNG", chú thích số đo "máy ảo".
- **Báo Claude:** `H-11 xong: video ở <đường dẫn>, dài <m:ss>.` ⇒ Claude xem lại đối chiếu "Không được nói".

### - [ ] H-12 · Ký APK bản thử nghiệm (30 phút) — dùng cho cài thử và thí điểm
1. Tạo keystore **ngoài repo**:
   `mkdir -p ~/secrets && keytool -genkeypair -v -keystore ~/secrets/hoicon-release.jks -alias hoicon -keyalg RSA -keysize 4096 -validity 10000`
2. **Sao lưu** `~/secrets/hoicon-release.jks` + mật khẩu ở 2 nơi (USB + trình quản lý mật khẩu). **Mất khóa = không cập nhật được app.**
3. Build (đặt biến trong terminal, không ghi vào tệp trong repo):
   `export HOICON_KEYSTORE_FILE=~/secrets/hoicon-release.jks HOICON_KEY_ALIAS=hoicon HOICON_KEYSTORE_PASSWORD=… HOICON_KEY_PASSWORD=…`
   rồi `apps/android/gradlew -p apps/android :app:assembleRelease` và `bash scripts/release-gate.sh` (phải ĐẠT).
4. Cài thử lên máy thật (H-06): `adb install -r apps/android/app/build/outputs/apk/release/app-release.apk`; ghi lại: có cảnh báo Play Protect
   không, có bị "**cài đặt bị hạn chế**" khi cấp quyền sàng lọc cuộc gọi / dữ liệu sử dụng / hiển thị trên ứng dụng khác không.
5. Tải APK lên **GitHub Releases** (đánh dấu *pre-release*), ghi phiên bản + ngày.
- **Báo Claude:** `H-12 xong: APK release ký xong, release-gate ĐẠT, cài máy thật <được / bị chặn ở bước …>.` ⇒ Claude ghi evidence 029.

### - [ ] H-13 · Chấm thử và nộp Vòng 1 (10–13/11)
1. **10/11**: gõ `Chạy judge chấm Vòng 1 với thuyết minh + video mới.` → sửa theo góp ý (lặp H-09 nếu cần).
2. Ôn 10 câu phản biện trong `docs/proposal/JUDGE-PRECHECK-2026-10-25.md`.
3. **13/11**: nộp theo email BTC: thuyết minh (PDF), video ≤ 3 phút, hình ảnh (nếu có). Chụp/lưu biên nhận.
- **Báo Claude:** `H-13 xong: đã nộp Vòng 1 lúc <giờ, ngày>, có biên nhận.` ⇒ Claude tick P1-04, cập nhật ROADMAP.

---

## Giai đoạn 3 — đưa code lên `main` và hạ tầng (tới 22/11)

### - [ ] H-14 · Push + PR + merge vào `main` (30 phút)
1. `git push origin tien-collab-dev`
2. Gõ `Soạn mô tả PR tien-collab-dev → main.` rồi `gh pr create --base main --head tien-collab-dev` (dán mô tả Claude soạn).
3. Chờ CI xanh trên GitHub; đọc lướt các tệp nhạy cảm (manifest Android, đồng ý, PII).
4. **Squash merge** trên GitHub.
5. Gõ `Đặt lại tien-collab-dev theo main.`
- **Báo Claude:** `H-14 xong: PR #<số> đã squash merge.`

### - [ ] H-15 · Sửa `CLAUDE.md` cho đúng "một người" (5 phút)
- Gõ: `Cho phép sửa CLAUDE.md: Tiến làm một mình, Tiến quyết phạm vi, tự duyệt PR.` ⇒ Claude sửa, bạn đọc lại rồi commit.
- **Báo Claude:** `H-15 xong.`

### - [ ] H-16 · Triển khai lên VPS (2–3 giờ) — cần H-05
Làm trên VPS (SSH), theo `docs/setup/VPS-DEPLOYMENT.md`:
1. `git clone` repo, `git checkout main`.
2. `cp infra/env.prod.example infra/.env.prod && chmod 600 infra/.env.prod`.
3. Sinh khóa: `openssl rand -hex 32` **mỗi lần một khóa** cho `HOICON_PHONE_PEPPER_1`, `HOICON_DATA_KEY_1`, `HOICON_BACKUP_KEY_1`,
   `HOICON_DEVICE_JWT_SECRET` (4 giá trị **khác nhau**); `openssl rand -hex 24` cho mật khẩu Postgres; `HOICON_BOOTH_CODE_KEY` (≥ 32 ký tự).
   Điền token Zalo (bot thí điểm) + khóa Anthropic (workspace `hoicon-pilot`, tạo riêng). **Sao lưu cả bốn khóa** vào trình quản lý mật khẩu.
4. `bash scripts/deploy-vps.sh --check` (chỉ kiểm) → hết lỗi thì `bash scripts/deploy-vps.sh`.
5. Áp role ít quyền: chạy `infra/postgres/roles.sql` theo hướng dẫn trong tệp (role `hoicon_app` không sở hữu bảng).
6. Kiểm: `curl -fsS https://app.<tên-miền>/readyz` → `{"status":"ok",...,"zalo_mode":"live"}`; `/docs` trả 404.
- **Báo Claude:** `H-16 xong: https://app.<…>/readyz 200, zalo_mode live.` ⇒ Claude tick 012 T010/T013.

### - [ ] H-17 · Webhook Zalo + tin thử thật (20 phút)
1. Trên VPS: `docker compose -f infra/compose.prod.yml --env-file infra/.env.prod exec backend python -m hoicon.ops.zalo_webhook set --url https://app.<tên-miền>`
2. `… exec backend python -m hoicon.ops.zalo_webhook info` → Đạt.
3. Tạo mã ghép: `… exec backend python -m hoicon.ops.pairing_code --family thu-nghiem` → nhắn bot `/start <mã>` từ Zalo của bạn.
- **Báo Claude:** `H-17 xong: webhook Đạt, đã ghép Zalo của tôi.` ⇒ Claude chạy một sự cố thử đầu–cuối, tick 012 T011.

### - [ ] H-18 · Sao lưu + giám sát (40 phút)
1. Bật timer sao lưu theo `docs/setup/VPS-DEPLOYMENT.md` §8 (`hoicon-backup.service` + `.timer`) → `systemctl enable --now hoicon-backup.timer`.
2. Chép bản sao lưu ra ngoài VPS (rclone lên Google Drive cá nhân hoặc máy nhà) — tệp đã mã hóa.
3. Thử khôi phục một lần theo `docs/setup/BACKUP.md` (lệnh `restore-check`).
4. Tạo giám sát miễn phí (UptimeRobot): ping `https://app.<tên-miền>/readyz` mỗi 5 phút, báo về email/điện thoại.
- **Báo Claude:** `H-18 xong: timer bật, restore-check Đạt, UptimeRobot chạy.` ⇒ Claude tick 012 T012/T014.

---

## Giai đoạn 4 — thí điểm và Vòng 2 (23/11 → 09/01)

### - [ ] H-19 · Hoàn thiện tài liệu thí điểm (1 giờ)
1. Mở `docs/setup/PILOT-ONBOARDING.md`, `docs/setup/PILOT-SUPPORT.md` → thay mọi `[CHỜ MINH ĐIỀN]`: người phụ trách = Tiến, số/kênh hỗ trợ
   (Zalo của bạn), giờ hỗ trợ.
2. Đọc lại văn bản đồng ý `docs/legal/consent/` (10 mục đích) → sửa chữ nếu cần → gõ cho Claude để đổi `draft` ⇒ `approved`.
- **Báo Claude:** `H-19 xong: đã điền tài liệu thí điểm, duyệt văn bản đồng ý.` ⇒ Claude tick 029 T009, 011 T010, đồng bộ chuỗi Android (011 T012).

### - [ ] H-20 · Duyệt 110 kịch bản eval (2–3 giờ, có thể chia nhiều buổi)
1. Gõ `Lập danh sách 110 kịch bản kèm URL nguồn để tôi kiểm.` ⇒ Claude xuất bảng.
2. Mở từng URL: còn sống + đúng thủ đoạn ⇒ đánh "OK"; chết/sai ⇒ "đổi nguồn".
- **Báo Claude:** `H-20 xong: <n> OK, <m> cần đổi nguồn: <danh sách id>.` ⇒ Claude đổi `draft` ⇒ `approved`, tìm nguồn thay cho mục lỗi.

### - [ ] H-21 · Thí điểm gia đình thật: ≥ 5 (M2 20/12) → ≥ 20 (M3 09/01) → ≥ 30 (G3 14/02)
1. Tuyển từ người làm khảo sát đồng ý tham gia; **chỉ người ≥ 18 tuổi**.
2. Đến nhà: cài APK (H-12), bật "cài ứng dụng không rõ nguồn gốc" giúp rồi tắt lại; đọc cùng bác màn đồng ý; ghép đôi; con cháu nhắn bot `/start`.
3. Ghi danh: `… exec backend python -m hoicon.ops.pilot enroll --family <id> --confirm-adult`.
4. Mỗi tuần hỏi người giám hộ: tin "mất bảo vệ" có đúng không; nhờ một người giám hộ duyệt + in thử hồ sơ một sự cố **demo**; nhờ một bác đọc
   thử màn đồng ý, ghi chỗ khó hiểu.
- **Báo Claude:** `H-21: đã có <n> gia đình (id …); tuần <k>: <ghi chú>.` (báo mỗi tuần) ⇒ Claude chạy `ops pilot report`, `phase-gate` M2/M3.

### - [ ] H-22 · M1 trên máy thật (trước 06/12)
- Một lượt thật: số lạ (điện thoại khác của bạn/bạn bè) gọi vào máy thật → mở app ngân hàng **giả** (`:demobank`) → dừng an toàn → tin Zalo tới
  điện thoại bạn. Quay màn hình lại.
- **Báo Claude:** `H-22 xong: M1 chạy trên máy thật, video ở <đường dẫn>.` ⇒ Claude chạy `phase-gate M1`.

### - [ ] H-23 · Nộp Vòng 2 (09/01)
1. Gõ `Chuẩn bị Vòng 2: kịch bản video 5 phút, nội dung poster, cập nhật thuyết minh theo số thí điểm.`
2. Dựng **poster** theo mẫu BTC; quay **video 5 phút**; sửa thuyết minh (Word) theo số liệu thí điểm thật.
3. Nộp: tài liệu Vòng 1 hoàn thiện + poster + MVP (link APK/web) + video ≤ 5 phút.
- **Báo Claude:** `H-23 xong: đã nộp Vòng 2 lúc <…>.`

### - [ ] H-24 · Chung kết (18/01–21/02)
1. Gõ `Soạn slide pitching 10 phút + chạy judge chấm.` → tập trả lời câu phản biện.
2. Gian trưng bày: gõ `Chuẩn bị chế độ gian /booth cho buổi chung kết.`
- **Báo Claude:** `H-24 xong.`

---

## Nhật ký tick (Claude ghi)

| Mã | Ngày xong | Ghi chú / commit |
|---|---|---|
| | | |
