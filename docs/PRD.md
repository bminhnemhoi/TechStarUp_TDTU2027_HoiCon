# PRD — HỏiCon MVP (Vòng 2)

> Trạng thái: **khung** (P0-05). Điền chi tiết user story + tiêu chí chấp nhận trước khi bắt đầu task P2 tương ứng.
> Nguồn: thuyết minh `docs/proposal/HoiCon_Ban_mo_ta_y_tuong_TSC2027.pdf` (mọi cam kết phải giữ — skill `pitch-sync`).

## Người dùng
- **Người được bảo vệ** (≥ 60 tuổi, ít rành công nghệ, Android, dùng app ngân hàng).
- **Người giám hộ** (con cháu, dùng Zalo hằng ngày, thường ở xa).
- **Người vận hành/BGK** (xem trace, eval, demo).

## User story (mã US-xx — mỗi task P2 tham chiếu tới đây)

| Mã | Story | Task | Tiêu chí chấp nhận (tóm tắt) |
|---|---|---|---|
| US-01 | Là con, tôi ghép đôi app của mẹ với Zalo của tôi trong < 5 phút | P2-02 | mã 6 số/QR, hết hạn 15', E1–E4, ghi đồng ý từng quyền |
| US-02 | Là mẹ, khi đang nghe số lạ mà mở app ngân hàng, tôi được nhắc dừng lại bằng giọng nói | P2-05 | SafePause p95 ≤ 3 s, offline, giữ 3 s để tiếp tục |
| US-03 | Là con, tôi nhận cảnh báo Zalo trong ≤ 10 s và bấm được hành động | P2-07 | mẫu giai đoạn 1, 4 nút, trả lời 1/2/3 |
| US-04 | Là mẹ, tôi bấm "Hỏi con" để con gọi lại ngay | P2-06 | — |
| US-05 | Là con, tôi thấy tóm tắt AI và đánh giá rủi ro có lý do | P2-08/09 | "Đây là trợ lý AI HỏiCon", ≤ 15 s |
| US-06 | Là mẹ/con, tôi tra cứu một số/link/QR đáng ngờ | P2-11 | E10, nguồn dẫn |
| US-07 | Là con, tôi duyệt hồ sơ vụ việc trước khi gửi | P2-16 | interrupt duyệt |
| US-08 | Là gia đình, chúng tôi diễn tập lừa đảo an toàn | P2-13 | cờ `is_drill`, debrief |
| US-09 | Là mẹ, tôi rút đồng ý / xóa dữ liệu bất cứ lúc nào | P2-02/20 | E12, `data_requests` |
| US-10 | Là BGK, tôi xem tác tử suy luận từng bước và thử toàn luồng trên web | P2-19 | `/trace`, `/sim` |

## Ngoài phạm vi MVP
iOS; đọc nội dung cuộc gọi/SMS; tự động chặn giao dịch; tích hợp trực tiếp ngân hàng; người dùng < 18 tuổi.
