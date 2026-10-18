# Văn bản đồng ý · `core_protection` · Nhờ HỏiCon trông chừng giúp bác

> **BẢN NHÁP — chờ Minh duyệt.** Chưa được đưa cho người dùng thật. Phiên bản và sha256: xem `manifest.json`.

<!-- BEGIN-TEXT -->
Đây là trợ lý AI HỏiCon.
Nhờ HỏiCon trông chừng giúp bác
Sau cuộc gọi với số lạ, HỏiCon để ý 10 phút. HỏiCon xem bác có mở ứng dụng ngân hàng, ví điện tử, chứng khoán hay ứng dụng điều khiển điện thoại từ xa không. Ngoài lúc đó, HỏiCon không xem bác dùng ứng dụng nào.
Nếu thấy dấu hiệu đáng ngờ, HỏiCon nhắc bác dừng lại một chút. Bác vẫn là người quyết định.
HỏiCon không nghe, không ghi âm cuộc gọi, không đọc tin nhắn và danh bạ. HỏiCon không biết số dư, giao dịch hay mã xác thực (OTP) của bác.
HỏiCon giữ thông tin về từng cuộc gọi lạ tối đa 90 ngày, ghi chép các lần nhắc dừng lại tối đa 12 tháng. HỏiCon không bán thông tin của bác.
Muốn dừng hay xóa thông tin, bác nhờ người đã hướng dẫn bác hoặc con bác. Bác chưa đồng ý cũng không sao.
<!-- END-TEXT -->

## Nguồn của từng con số (không hiển thị cho người dùng)
- "10 phút", danh sách ứng dụng, không nghe/ghi âm/đọc tin nhắn/danh bạ: chữ app hiện tại `disclosure_1_*`, `disclosure_2_*`; ADR-001; CLAUDE.md luật 3.
- "Bác vẫn là người quyết định": CLAUDE.md luật 4 (không bao giờ chặn vĩnh viễn).
- "90 ngày": `docs/DATA-MODEL.md` §6 (`risk_events`). Hồ sơ vụ việc giữ lâu hơn (12 tháng sau khi đóng) và được nêu ở `guardian_alerts`.
- Rút lại/xóa: `docs/PRIVACY-DPIA.md` (xóa qua đội thí điểm; màn E12 trên app chưa có).

## Điểm chờ quyết
- Chữ app hiện tại (`disclosure_*`) gộp bốn thẻ; bản này ngắn hơn. Minh quyết giữ bản ngắn hay bản bốn thẻ.
- Chữ app hiện tại nói "tối đa 90 ngày" cho mọi thứ; thực tế hồ sơ vụ việc giữ 12 tháng. Bản này tách ra (xem `guardian_alerts`).
- Sửa theo `ux-elder-reviewer` (18/10): một câu hạn lưu thống nhất với `guardian_alerts` (#7), đường rút lại cụ thể hơn (#8), "(OTP)" (#31), "thông tin" thay "dữ liệu" (#28), "không sao" khi chưa đồng ý (#27).
- Reviewer đề xuất chia 4 thẻ có nút "Nghe lại" thay vì một khối (#26) và thêm câu tóm tắt đầu (#25): để làn A/Minh quyết.
- Reviewer lưu ý "con bác" chưa chắc là con (#16): để app chèn tên người giám hộ.
