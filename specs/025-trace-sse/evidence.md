# Bằng chứng nghiệm thu Spec 025: Luồng SSE Truy vết Tác tử

- **Ngày đo**: 16/10/2026
- **Môi trường**: Dev Linux / Docker Postgres 17 / FastAPI Uvicorn
- **Cam kết**: 0 số điện thoại thô, 0 HMAC h1, 100% che mờ PII trên luồng SSE

## Bảng kết quả tiêu chí thành công

| Tiêu chí | Mô tả | Ngưỡng yêu cầu | Kết quả thực tế | Trạng thái |
|---|---|---|---|---|
| SC-001 | Độ trễ phát bước mới (SSE Latency) | p95 ≤ 500 ms | Đang chờ triển khai và đo lường thực tế | CHƯA ĐO |
| SC-002 | Bảo vệ quyền riêng tư & Che mờ PII | 100% che mờ PII | Đang chờ triển khai và đo lường thực tế | CHƯA ĐO |
| SC-003 | Heartbeat chống ngắt kết nối (Keep-Alive) | Gửi `: ping` mỗi 15s | Đang chờ triển khai và đo lường thực tế | CHƯA ĐO |
| SC-004 | Truy vấn lịch sử đầy đủ (`/v1/runs/{id}/steps`) | 100% khớp lịch sử DB | Đang chờ triển khai và đo lường thực tế | CHƯA ĐO |
| SC-005 | Đóng luồng tất định (`event: done`) | Phát event done khi xong | Đang chờ triển khai và đo lường thực tế | CHƯA ĐO |

## Nhật ký kiểm thử & đo lường
(Sẽ được cập nhật sau khi hoàn thành các tasks triển khai)
