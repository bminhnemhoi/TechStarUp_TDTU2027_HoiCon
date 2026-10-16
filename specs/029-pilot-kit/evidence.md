# Bằng chứng nghiệm thu Spec 029: Bộ thí điểm & Play internal v0.3

- **Trạng thái**: chưa triển khai. Đã có spec, plan và tasks từ 16/10/2026; chưa có số đo nào.
- **Điều kiện vào giai đoạn 2**: `012-release-and-hosting` (chưa có spec), `034-hardening-core` (chưa thi công), W0-3
  Play Console + Firebase (⏸). Giai đoạn 1 không phụ thuộc các mục này.
- **Nguồn số dự kiến**: pytest và máy ảo ở giai đoạn 1; VPS + máy thật + Android vitals (nhập tay, ghi cỡ mẫu) ở giai
  đoạn 2.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 heartbeat ở máy chủ | khớp thân Android; cập nhật thiết bị; từ chối khi chưa đồng ý/thu hồi; 429 ở lần 9/giờ | `test_heartbeat.py` + log AVD (200 thay vì 404) | chưa chạy | CHƯA ĐO |
| SC-002 báo cáo sức khỏe | độ phủ đúng (100/50/0%), mẫu số đúng khi ghép giữa kỳ; không PII | `test_ops_pilot.py` | chưa chạy | CHƯA ĐO |
| SC-003 `release-block` tự động | APK debug ⇒ TRƯỢT đúng mục; bản release của 012 ⇒ ĐẠT | `test_release_gate.py` + chạy trên AAB release | chưa chạy | CHƯA ĐO |
| SC-004 tài liệu thí điểm | `PILOT-ONBOARDING` (≤ 5 phút, theo hãng), `PILOT-SUPPORT`; reviewer + Minh duyệt | review | chưa chạy | CHƯA ĐO |
| SC-005 Gate M2 | ≥ 5 gia đình, ≥ 1 máy thật, độ phủ heartbeat ≥ 90% (7 ngày), crash-free ≥ 99% (Play vitals, ghi cỡ mẫu), 0 High | `ops pilot gate-m2` + ảnh Play Console | BLOCKED (012, 034, W0-3) | CHƯA ĐO |
| SC-006 hồi quy | pytest, Gradle, eval smoke xanh; đường dừng an toàn không đổi | CI | chưa chạy | CHƯA ĐO |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| `python3 scripts/check-spec-trace.py` (sau khi tạo bộ spec) | xem báo cáo phiên 16/10/2026 |

## Phát hiện khi thiết kế (16/10/2026)

- Android (022) gửi `POST /v1/heartbeat` mỗi 15 phút nhưng máy chủ **chưa có route này**. Thiết bị nhận 404 (Android ánh
  xạ thành `ServerError`), và `devices.last_heartbeat_at` chỉ được ghi lúc ghép đôi. T003 sửa việc này.
- Android ánh xạ mọi 403 thành "chưa xác thực" ⇒ T005.
