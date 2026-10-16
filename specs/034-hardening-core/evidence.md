# Bằng chứng nghiệm thu Spec 034: Gia cố lõi trước người dùng thật

- **Trạng thái**: chưa triển khai. Đã có spec, plan và tasks từ 16/10/2026; chưa có số đo nào.
- **BLOCKED một phần bởi 012** (chưa có spec): lịch chạy sao lưu trên VPS, nơi lưu ngoài máy, áp role DB ở prod.
- **Môi trường dự kiến**: Linux CachyOS, Postgres dev trong Docker (cổng 15432), uvicorn.
- **Nguồn số**: máy dev; thời gian khôi phục đo trên dữ liệu dev, không đại diện cho prod.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 hạn lưu | 100% dòng quá hạn được xử lý; 0 dòng trong hạn bị đụng; `consents` nguyên; lũy đẳng; lô ≤ 1.000 | `test_retention.py` | chưa chạy | CHƯA ĐO |
| SC-002 xóa theo yêu cầu | 0 dòng nhận diện trong mọi bảng có `family_id`/`incident_id` + checkpoint; `consents` nguyên; tombstone ẩn danh; JWT cũ ⇒ 401 | `test_purge_family.py` | chưa chạy | CHƯA ĐO |
| SC-003 sao lưu & khôi phục | bản mã không đọc được khi thiếu khóa; sửa/cắt ⇒ lỗi; khôi phục khớp manifest + trigger `ALWAYS`; có thời gian khôi phục | `test_backup_restore.py` + `ops backup restore-check` | chưa chạy | CHƯA ĐO |
| SC-004 đồng ý ở máy chủ | rút `core_protection` ⇒ 403, không ghi; thiếu `guardian_alerts` ⇒ không gửi Zalo | `test_consent_enforcement.py` | chưa chạy | CHƯA ĐO |
| SC-005 mặc định an toàn | không đặt env ⇒ prod; `/readyz` báo khóa thiếu; thân > 256 KB ⇒ 413 | `test_ops_safety.py` | chưa chạy | CHƯA ĐO |
| SC-006 review bảo mật | 0 Critical, 0 High chưa xử lý trên toàn codebase | `privacy-audit` + `security-privacy-reviewer` (T016) | chưa chạy | CHƯA ĐO |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| `python3 scripts/check-spec-trace.py` (sau khi tạo bộ spec) | xem báo cáo phiên 16/10/2026 |
