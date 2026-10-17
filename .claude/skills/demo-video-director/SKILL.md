---
name: demo-video-director
description: "Đạo diễn kịch bản video demo sản phẩm (Video 3 phút cho Vòng 1 theo task P1-03 và Video 5 phút cho Vòng 2 theo task P2-21). Hướng dẫn chi tiết phân cảnh theo từng giây (timecode), lời thoại voiceover truyền cảm hứng, và đường dẫn thao tác bấm máy (click-path) trên máy ảo AVD hoặc máy thật để quay một lần ăn ngay."
---

# Demo Video Director (HỏiCon Pitch & Product Showcase)

Kỹ năng này chịu trách nhiệm **chỉ đạo nghệ thuật & biên kịch kỹ thuật** cho các video demo nộp ban giám khảo Tech Startup Challenger 2027.

---

## 1. Cấu Trúc Phân Cảnh Video 3 Phút Chuẩn Vòng 1 (Task P1-03)

| Mốc Giờ | Phân Cảnh | Thao Tác Màn Hình (Click-Path) | Lời Thoại Thuyết Minh (Voice-Over) |
|---|---|---|---|
| **00:00 - 00:25** | **Nỗi đau & Bối cảnh** | Quay khuôn mặt người cao tuổi trầm ngâm bên chiếc điện thoại, phóng sự lừa đảo tiền tỷ thoáng qua. | *"Mỗi ngày tại Việt Nam, hàng trăm người cao tuổi bị các nhóm lừa đảo công nghệ thao túng tâm lý, cướp đi toàn bộ số tiền dưỡng già tích cóp cả đời. Là con cái, chúng ta không thể ở bên cha mẹ 24/7."* |
| **00:25 - 00:50** | **Kích hoạt bẫy lừa đảo** | Trên AVD `hc-api36`: Kẻ lừa đảo gọi tới từ số lạ (cuộc gọi hiển thị "Số lạ - Cảnh báo"). Cuộc gọi kết thúc $\rightarrow$ Cửa sổ rủi ro 600s mở ngầm. | *"HỏiCon ra đời như một người gác cổng thầm lặng. Khi có cuộc gọi từ số lạ kết thúc, hệ thống Sentinel tự động kích hoạt Cửa sổ rủi ro bảo vệ."* |
| **00:50 - 01:30** | **SafePause kích hoạt tức thì** | Mở app `:demobank`, người dùng bấm chuyển tiền $\rightarrow$ **SafePause bung ra ngay lập tức (< 2s)**. Giọng nói AI vang lên đọc cảnh báo. | *"Ngay khi mẹ vừa mở ứng dụng ngân hàng để chuyển tiền, SafePause lập tức can thiệp. Không cần chờ máy chủ, hệ thống tự động giữ nhịp an toàn và đọc to cảnh báo: 'Bác ơi, cẩn thận kẻ lừa đảo đang hối thúc!'."* |
| **01:30 - 02:15** | **Cảnh báo Zalo & Can thiệp của con** | Chuyển cảnh sang màn hình điện thoại người con: Bot Zalo nảy thông báo khẩn $\rightarrow$ Con bấm link `/a/[token]` $\rightarrow$ Xem chi tiết và bấm "Đã gọi cho mẹ / An toàn". | *"Cùng lúc đó, chuông điện thoại của người con reo lên. Một cảnh báo tức thời gửi qua Zalo kèm phân tích rủi ro. Chỉ với một cú chạm, người con đã kịp thời can thiệp bảo vệ mẹ mình."* |
| **02:15 - 03:00** | **Tuyên ngôn công nghệ & Kêu gọi** | Màn hình hiển thị logo HỏiCon, các chỉ số: 100% WCAG AAA, 0 số điện thoại thô, bảo vệ ngoại tuyến $\le 3$s. | *"HỏiCon — Không chỉ là AI, mà là sự an tâm của con cái gửi trọn cho cha mẹ. Tết này, hỏi con trước khi chuyển tiền!"* |

---

## 2. Kỹ Thuật Quay "One-Take" (Bấm Máy 1 Lần Ăn Ngay)

Để quay video mượt mà không bị vấp:

1. **Chuẩn bị dữ liệu mẫu sạch**:
   - Chạy lệnh nạp dữ liệu demo: `python scripts/emu-scenario.py reset`.
   - Đảm bảo AVD `hc-api36` đã cài app `:app` và `:demobank`.
2. **Kịch bản lệnh bấm (Shell Script Driven)**:
   - Thay vì bấm tay lúng túng, kích hoạt cuộc gọi giả bằng lệnh adb:
     ```bash
     python scripts/emu-scenario.py call-incoming --number "+84900000001"
     ```
3. **Thu âm giọng nói (Audio Voice-Over)**:
   - Dùng giọng đọc tiếng Việt ấm áp, tốc độ vừa phải (120–130 từ/phút), âm sắc thể hiện sự chân thành và bảo vệ gia đình.
