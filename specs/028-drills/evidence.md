# Bằng chứng nghiệm thu Spec 028: Diễn tập nhận biết lừa đảo v1

- **Trạng thái**: chưa triển khai. Đã có spec, plan và tasks từ 16/10/2026; chưa có số đo nào.
- **Phụ thuộc nội dung**: 3 kịch bản diễn tập sẽ ở `approved: false` cho tới khi Minh duyệt (P1-07). Bản prod từ chối
  kịch bản chưa duyệt.
- **Môi trường dự kiến**: Linux CachyOS, Postgres dev (cổng 15432), uvicorn, AVD `hc-api36`, Zalo **mock**.
- **Nguồn số**: máy dev và máy ảo (máy ảo ≠ máy thật).

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 `is_drill` ở mọi nơi | 100% đối tượng diễn tập mang `is_drill` / `[DIỄN TẬP]`; tin Zalo có câu công khai AI | `test_api_drills.py`, `test_drill_schemas.py`, test UI | chưa chạy | CHƯA ĐO |
| SC-002 không hạ cấp sự cố thật | `drill_id` không hợp lệ ⇒ sự cố thật; 0 đường hạ cấp | `test_drill_flag_guard.py` (ma trận 6 ca) | chưa chạy | CHƯA ĐO |
| SC-003 giới hạn & đồng ý | chưa đồng ý / quá 2 bài/tháng / ngoài khung / chưa duyệt (prod) ⇒ từ chối; "Để lúc khác" ⇒ `declined` | `test_api_drills.py`, test JVM | chưa chạy | CHƯA ĐO |
| SC-004 E11 | 8 ảnh (4 màn × 100/200%); ≥ 20sp, ≥ 64dp, ≤ 2 hành động, ≥ 7:1, `[DIỄN TẬP]` luôn hiện, đọc to | ảnh `~/hoicon-evidence/028-drills/` + `ux-elder-reviewer` | chưa chạy | CHƯA ĐO |
| SC-005 E2E máy ảo | đặt lịch ⇒ nhận ≤ 1 nhịp heartbeat ⇒ hoàn thành ⇒ kết quả lên máy chủ (cả khi mất mạng) ⇒ tin `[DIỄN TẬP]` | E2E AVD API 36 (T019) | chưa chạy | CHƯA ĐO |
| SC-006 chỉ dữ liệu tất định | chỉ mã lựa chọn; 0 văn bản tự do / ghi âm; 0 lời gọi LLM | test hợp đồng + quét DB + grep `llm_router` trong mã mới | chưa chạy | CHƯA ĐO |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| `python3 scripts/check-spec-trace.py` (sau khi tạo bộ spec) | xem báo cáo phiên 16/10/2026 |

## Cần Minh/Tiến quyết (★)

- Chỉ số PILOT-PROTOCOL: v1 đo tỷ lệ vượt qua / hoàn thành / từ chối, không đo "tỷ lệ phát hiện bằng cảm biến" (spec §2).
- Duyệt 3 kịch bản diễn tập trước thí điểm.
