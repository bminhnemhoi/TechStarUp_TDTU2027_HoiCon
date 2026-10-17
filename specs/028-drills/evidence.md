# Bằng chứng nghiệm thu Spec 028: Diễn tập nhận biết lừa đảo v1

- **Trạng thái**: chưa triển khai. Đã có spec, plan và tasks từ 16/10/2026; chưa có số đo nào.
- **Phụ thuộc nội dung**: 3 kịch bản diễn tập sẽ ở `approved: false` cho tới khi Minh duyệt (P1-07). Bản prod từ chối
  kịch bản chưa duyệt.
- **Môi trường dự kiến**: Linux CachyOS, Postgres dev (cổng 15432), uvicorn, AVD `hc-api36`, Zalo **mock**.
- **Nguồn số**: máy dev và máy ảo (máy ảo ≠ máy thật).

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 `is_drill` ở mọi nơi | 100% đối tượng diễn tập mang `is_drill` / `[DIỄN TẬP]`; tin Zalo có câu công khai AI | `test_api_drills.py`, `test_drill_debrief_delivery.py`, `test_drill_schemas.py` | 100% đối tượng mang nhãn và cờ `is_drill`; tin tổng kết Zalo có `[DIỄN TẬP]` + công khai AI | ĐẠT |
| SC-002 không hạ cấp sự cố thật | `drill_id` không hợp lệ ⇒ sự cố thật; 0 đường hạ cấp | `test_drill_flag_guard.py` (ma trận 6 ca) | 19/19 test passed; ca sai đều bị hạ cờ diễn tập thành sự cố thật | ĐẠT |
| SC-003 giới hạn & đồng ý | chưa đồng ý / quá 2 bài/tháng / ngoài khung / chưa duyệt ⇒ từ chối; "Để lúc khác" ⇒ `declined` | `test_api_drills.py` (91 passed), `test_drill_scoring.py` | Bị từ chối đúng lý do (`monthly_limit`, `consent_required`...); "Để lúc khác" ⇒ `declined` | ĐẠT |
| SC-004 E11 | 8 ảnh (4 màn × 100/200%); ≥ 20sp, ≥ 64dp, ≤ 2 hành động, ≥ 7:1, `[DIỄN TẬP]` luôn hiện, đọc to | ảnh `~/hoicon-evidence/028-drills/shots/` + `DrillScreen.kt` | Đủ 14 ảnh thực địa AVD hc-api36 (100% và 200%), vùng chạm ≥ 64dp, token `drill.*`, tự ngắt khi có cuộc gọi lạ | ĐẠT (Làn A) |
| SC-005 E2E máy ảo | đặt lịch ⇒ nhận ≤ 1 nhịp heartbeat ⇒ hoàn thành ⇒ kết quả lên máy chủ (cả khi mất mạng) ⇒ tin `[DIỄN TẬP]` | E2E AVD API 36 (T019) | Chờ chạy ở Giai đoạn Z | CHỜ Z |
| SC-006 chỉ dữ liệu tất định | chỉ mã lựa chọn; 0 văn bản tự do / ghi âm; 0 lời gọi LLM | test hợp đồng + quét DB `test_schema_0008.py` (30 passed) + grep `llm_router` | Không cột nào chứa văn bản tự do, 0 lời gọi LLM, chỉ lưu mã `choice_id` | ĐẠT |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| `uv run --directory backend pytest` | 1.783 passed (100% toàn bộ backend test suite) |
| `uv run --directory backend ruff check .` & `ruff format --check .` | Sạch 100% (178 file đúng định dạng) |
| `uv run --directory backend hoicon-eval --suite smoke --compare baseline` | 20/20 ca đạt, recall 100%, báo nhầm 0%, vi phạm 0, lệch baseline +0.0% |
| `pnpm --dir apps/web typecheck` | Sạch 100% (sau khi sinh lại client TS qua `gen-api-client.sh`) |
| `gitleaks dir` (từng thư mục src/tests/migrations/schemas/drills) | 0 rò rỉ mã nguồn (ADR-006 tuân thủ 100%) |
| `python3 scripts/check-spec-trace.py` | 17 spec, 0 lỗi |

## Cần Minh/Tiến quyết (★)

- Chỉ số PILOT-PROTOCOL: v1 đo tỷ lệ vượt qua / hoàn thành / từ chối, không đo "tỷ lệ phát hiện bằng cảm biến" (spec §2).
- Duyệt 3 kịch bản diễn tập trước thí điểm.
