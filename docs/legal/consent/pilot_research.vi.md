# Văn bản đồng ý · `pilot_research` · Giúp HỏiCon học cách làm tốt hơn

> **BẢN NHÁP — chờ Minh duyệt.** Chưa được đưa cho người dùng thật. Phiên bản và sha256: xem `manifest.json`.

<!-- BEGIN-TEXT -->
Giúp HỏiCon làm tốt hơn
HỏiCon đang được dùng thử cùng một nhóm nhỏ. HỏiCon xin phép ghi lại một số thông tin để biết ứng dụng có giúp được bác không.
Đó là: ứng dụng có chạy ổn không, bác còn bật các quyền bảo vệ không, và các buổi tập có giúp bác nhận ra lừa đảo dễ hơn không.
HỏiCon không ghi nội dung cuộc gọi hay tin nhắn. Khi báo cáo, các con số được gộp chung nhiều người, không có tên bác.
Bác muốn rút hay xóa thông tin, bác nhờ người đã hướng dẫn bác cài HỏiCon. Bác chưa đồng ý cũng không sao.
<!-- END-TEXT -->

## Nguồn của từng con số (không hiển thị cho người dùng)
- Các số thu: `docs/PILOT-PROTOCOL.md` ("Số liệu thu"); heartbeat (spec 029): trạng thái quyền + phiên bản ứng dụng mỗi 15 phút, `ops pilot report` không có PII (`pilot_report.v1.json`).
- "18 tuổi": CLAUDE.md luật 8. "Xóa nếu nhờ": spec 034 (`purge_family`).

## Điểm chờ quyết
- **CHẶN TRƯỚC KHI DUYỆT:** mã hiện không kiểm đồng ý `pilot_research` (heartbeat kiểm `core_protection`). Cần quyết heartbeat/báo cáo thí điểm có phải đòi `pilot_research` không.
- "Báo cáo chỉ nêu số tổng hợp": `ops pilot report` hiện in theo từng gia đình dưới dạng đã ẩn danh; xác nhận đó là "tổng hợp" theo nghĩa Minh muốn.
- Crash-free lấy từ Play vitals (Google), không do HỏiCon thu: có cần nói ra không.
- Sửa theo `ux-elder-reviewer` (18/10): bỏ "đang tham gia" (áp đặt, #5), bỏ chữ nghe như chấm điểm (#11), bỏ dòng "từ 18 tuổi" khỏi chữ hiển thị (#29: đã ở `PILOT-PROTOCOL.md`), thêm cách rút (#4).
- Câu "gộp chung nhiều người" CHỈ đúng sau khi chốt `ops pilot report` gộp thật (hiện in theo từng gia đình đã ẩn danh).
