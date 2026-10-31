# Checklist riêng tư & an toàn — Spec 033 (`/sim`, `/trace`, `/eval`)

Người tick: `security-privacy-reviewer` hoặc Tiến (T017).

- [ ] Cổng `HOICON_SIM_ENABLED` mặc định tắt; `compose.prod.yml` không đặt; tắt ⇒ 404 mọi `/v1/sim/*`, `/v1/eval/*`
- [ ] Chỉ phiên người giám hộ của gia đình `is_demo`; gia đình thật ⇒ 404 (không lộ sự tồn tại)
- [ ] Sự cố sim mang cờ `sim` ⇒ Zalo mock kể cả khi `HOICON_ZALO_MODE=live`; 0 lời gọi `LiveZaloClient`
- [ ] Sim đi đúng đường `/v1/events` + đồ thị + route quyết định thật (không có đường tắt làm demo "đẹp hơn" sản phẩm)
- [ ] Phản hồi API + DOM: 0 số điện thoại/h1/tên gói/lời kể; tin mở đầu câu công khai AI (lược đồ bắt)
- [ ] Hạn mức 10 lượt/giờ/phiên, 3 lượt đang chạy/gia đình; `live` tính vào trần chi tiêu của `llm_router`
- [ ] `/trace` của gia đình khác ⇒ "Không tìm thấy"; `/v1/graphs/incident` chỉ mô tả cấu trúc mã
- [ ] `/eval` chỉ đọc baseline đã commit, có dòng "CHƯA PHẢI SỐ M3" khi verdict ≠ `pass`
