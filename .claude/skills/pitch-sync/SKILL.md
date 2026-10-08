---
name: pitch-sync
description: Đối chiếu cam kết trong thuyết minh/video/poster/slide HỏiCon với trạng thái thật của sản phẩm và số liệu đo được, theo tiêu chí thể lệ Tech Startup Challenger 2027; cập nhật thuyết minh bằng pipeline docs/proposal/src khi cần. Dùng trước khi nộp Vòng 1 (10/11), sau gate M1–M3, trước quay video và trước chung kết.
---

# pitch-sync

## 1. Thu thập cam kết
- Trích các cam kết có thể kiểm chứng từ `docs/proposal/HoiCon_Ban_mo_ta_y_tuong_TSC2027.pdf` (đặc biệt Bảng mục tiêu, kế hoạch tuần Vòng 2, đội ngũ, tính năng, chỉ số AI, số gia đình thí điểm, tài chính).
- Với mỗi cam kết: `| Cam kết | Vị trí | Trạng thái thật | Bằng chứng | Hành động |`.

## 2. Phân loại
- **Đã đạt** (có bằng chứng: báo cáo gate, eval, ảnh, số thí điểm).
- **Đang làm đúng hạn**.
- **Lệch** ⇒ đề xuất sửa sản phẩm hoặc sửa câu chữ thuyết minh cho trung thực (ví dụ quy mô thí điểm, thành phần đội, máy ảo vs máy thật).

## 3. Cập nhật thuyết minh (khi Minh đồng ý)
- Sửa nội dung trong `docs/proposal/src/build.js` (và `model.py` nếu đổi số tài chính), chạy lại pipeline theo `docs/proposal/src/README.md`, xuất Word + PDF qua `convert.ps1`.
- Giữ định dạng thể lệ: tiếng Việt, Times New Roman 14, A4.

## 4. Chấm thử
- Gọi tác tử `judge` với tài liệu mới; tổng hợp 10 câu hỏi phản biện và chuẩn bị câu trả lời có số liệu.
