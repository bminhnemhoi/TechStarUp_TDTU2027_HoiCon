# Bằng chứng nghiệm thu Spec 032: Coach hằng tuần + báo "mất bảo vệ"

- **Trạng thái (18/10/2026)**: chỉ có spec/plan/tasks. **Chưa code.** Không có hợp đồng mới trong `docs/schemas/` (xem tasks.md).
- **Nguồn số dự kiến**: pytest (đồng hồ giả) + AVD `hc-api36` cho khoảng trống heartbeat (máy ảo ≠ máy thật); máy thật BLOCKED.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 phát hiện đúng | `silent` 24 giờ ± 1; `permission_off` 2 khung; 0 tin khi không đủ điều kiện | pytest | chưa chạy | CHƯA ĐO |
| SC-002 một tin mỗi đợt | 48 lần chạy ⇒ 1 tin | pytest | chưa chạy | CHƯA ĐO |
| SC-003 bản tin đúng số | khớp seed; 0 câu "an toàn" khẳng định | pytest | chưa chạy | CHƯA ĐO |
| SC-004 hạn mức | 80% / 95% đúng hành vi; tin sự cố không ảnh hưởng | pytest | chưa chạy | CHƯA ĐO |
| SC-005 công khai AI + PII | 100% công khai; 0 PII | pytest | chưa chạy | CHƯA ĐO |
| SC-006 ngưỡng 24 giờ | khoảng trống dài nhất trên AVD < 24 giờ | AVD | chưa chạy | CHƯA ĐO |
| SC-007 máy thật | tỷ lệ báo nhầm 7 ngày thí điểm | thí điểm | — | BLOCKED (029 giai đoạn 2) |
