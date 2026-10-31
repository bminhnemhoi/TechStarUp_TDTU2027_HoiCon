# Kịch bản video 3 phút — Vòng 1 (P1-03)

Soạn 25/10/2026 (nhà điều phối, skill `demo-video-director`), **đã đối chiếu với sản phẩm thật** ở `tien-collab-dev` 4afb1b1.
Quay 05–08/11. Mọi số điện thoại, tên, ngân hàng là **hư cấu** (luật 8): app ngân hàng là `:demobank` ("Ngân hàng Mẫu"), số gọi lấy từ
`data/fixtures/phones.json`. Mọi số liệu trên màn hình có nguồn; số đo trên máy ảo phải ghi "máy ảo".

## Chuẩn bị (một lần, ~20 phút)
1. `bash scripts/emu-start.sh hc-api36` (có cửa sổ để quay; **chờ ≥ 3 phút** sau khi khởi động — `docs/EMULATOR.md`), cài bản release/demo
   (`apps/android/gradlew -p apps/android :app:assembleDemo :demobank:assembleDebug` + `adb install -r …`). Cấp quyền, ghép đôi theo
   `.handover` làn A (gia đình demo `w6-gia-dinh`, API 18001). Cỡ chữ máy ảo 100% (cảnh phụ: 200%).
2. Backend dev + web: `docs/setup/SIM.md`. Người giám hộ demo: `ops guardian_link --seed` ⇒ mở trang hành động trên trình duyệt thứ hai
   (vai "điện thoại của con"). Zalo thật chưa có token (W0-3) ⇒ cảnh Zalo dùng **`/sim` cột "Zalo của con (mô phỏng)"** và ghi rõ trên video.
3. Thử một lượt: `python scripts/emu-scenario.py --avd hc-api36 --scenario fake_police --runs 1` (phải hiện E7).

## Phân cảnh

| Mốc | Cảnh | Thao tác (click-path) | Lời thoại (≈ 125 từ/phút) |
|---|---|---|---|
| 00:00–00:20 | Nỗi đau | Ảnh tĩnh/tiêu đề báo về lừa đảo giả danh công an (dẫn nguồn trên màn hình như thuyết minh [1], [7]) | "Năm 2025, lừa đảo trực tuyến lấy đi hơn tám nghìn tỷ đồng. Thủ đoạn số một là giả danh công an — và nạn nhân thường là cha mẹ chúng ta." |
| 00:20–00:40 | Cuộc gọi lạ | `python scripts/emu-scenario.py --avd hc-api36 --scenario fake_police --runs 1` (giả lập cuộc gọi đến từ số lạ hư cấu; bác nghe máy) | "Một số lạ gọi cho bà Lan, xưng là công an, bảo bà chuyển tiền để xác minh." |
| 00:40–01:20 | **Khoảng dừng an toàn (E7)** | Trong lúc còn đang gọi, script mở "Ngân hàng Mẫu" ⇒ E7 hiện: "Bác ơi, khoan chuyển tiền đã" + tự đọc to; giữ khung 5 giây trên màn hình | "Khi bà mở ứng dụng ngân hàng trong lúc vẫn đang nghe máy, Lính gác bật khoảng dừng an toàn — ngay trên điện thoại, không cần mạng, không cần AI. HỏiCon không ghi âm, không đọc giao dịch." Chú thích nhỏ: "p95 ≤ 1,21 giây (bản phát hành, máy ảo Android 14 và 16)" |
| 01:20–01:45 | Hỏi nhanh (E8) | Vài giây sau, máy chủ gửi câu hỏi: E8 hiện một câu ngắn, bà trả lời bằng một trong hai nút chính (nút "Hỏi con" ở E7 là đường riêng: mở bàn phím gọi trống) | "Trợ lý AI hỏi bà một câu ngắn, lấy từ danh sách câu hỏi đã duyệt, để chấm mức rủi ro. AI chỉ được nâng mức cảnh báo, không bao giờ hạ." |
| 01:45–02:20 | Con nhận cảnh báo | Trình duyệt thứ hai: tin mở đầu "Đây là trợ lý AI HỏiCon" + tóm tắt ⇒ trang hành động ⇒ "Gọi điện cho mẹ" ⇒ "Đã gọi được, mẹ an toàn" ⇒ xác nhận | "Anh Minh nhận tin kèm tóm tắt. Một chạm để gọi mẹ, một chạm để xác nhận mẹ an toàn." Nhãn góc màn hình: "MÔ PHỎNG — dữ liệu hư cấu" |
| 02:20–02:30 | Trợ lý AI làm gì | `/trace/<runId>`: sơ đồ các bước đã chạy + bản chữ | "Mọi bước trợ lý AI đã làm trong lượt này đều xem lại được." |
| 02:30–02:45 | Đội và mô hình | Thẻ chữ: đội 2 thành viên + đội tác tử AI; gói Gia đình 49.000 đồng/tháng; đối tác ngân hàng (B2B2C) | "Gói Gia đình 49.000 đồng một tháng; ngân hàng và nhà mạng là kênh phân phối." (số theo thuyết minh đã sửa) |
| 02:45–03:00 | Kêu gọi | Logo + câu chốt; dòng nhỏ: ngày thí điểm **khớp thuyết minh đã sửa** (hiện thuyết minh ghi 11/2026; Play Console chưa đăng ký) | "HỏiCon — đưa gia đình trở lại cuộc trò chuyện. Hỏi con trước khi chuyển tiền." |

## Không được nói/hiện (chưa đo hoặc không đúng)
- Không nêu recall, tỷ lệ báo nhầm, "100% WCAG", số gia đình đang dùng: chưa có số đo thật (pitch-sync #7, #9).
- Không quay Zalo thật hay số điện thoại thật; không nói "đã có trên Google Play" (chưa đăng ký Play Console).
- Không nói "hoạt động trên mọi máy" — chỉ đã đo trên máy ảo Android 14 và 16.

## Việc của người
Quay màn hình (máy ảo + trình duyệt), thu giọng đọc, dựng (có thể dùng skill `video-use`), kiểm ≤ 3:00, `judge` xem trước 10/11.

## Sửa theo `judge` (25/10)
Đã sửa 3 câu có nguy cơ tuyên bố quá mức (01:20 câu hỏi từ danh sách đã duyệt; 01:45 bỏ "ngay"; 02:20 "lượt này" thay vì "năm tác tử"), thêm 15 giây đội + mô hình doanh thu, thống nhất ngày thí điểm với thuyết minh.
