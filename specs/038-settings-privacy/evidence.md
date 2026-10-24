# Evidence 038 — Cài đặt & quyền riêng tư (E12)

## Lượt 10 — T002 `POST /v1/data-requests` (làn B, 25/10/2026)
- Router mới `api/routers/data_requests.py` + `purge_service.request_delete_detailed` (trả thêm cờ `created`; `request_delete` cũ giữ nguyên hành vi) + mẫu tin `texts.guardian_data_delete_notice` (mở đầu "Đây là trợ lý AI HỏiCon").
- Test (đỏ ở bước thu thập vì chưa có router, rồi xanh): `tests/contract/test_data_request_schema.py` (fixture valid/invalid) và `tests/integration/test_api_data_requests.py` 13 ca: chỉ thiết bị `protected`, 202 mới / 200 lũy đẳng, 3/ngày rồi 429 kèm `Retry-After`, 401 không token/token lạ, thân sai ⇒ 422 và không ghi gì (gồm trường tự do), ghi `requested_via='app'`, tin báo xếp TRƯỚC purge (purge hoãn 120 giây) và CHỈ khi còn `guardian_alerts` (đã rút ⇒ 0 tin, vẫn 202), rút `core_protection` vẫn xóa được, sau purge token cũ 401.
- Verify: `pytest tests/contract tests/integration/test_api_data_requests.py tests/integration/test_purge_family.py` 351 passed; ruff sạch. Client TS sinh lại (web chưa dùng).
- **Chủ ý không qua `consent_gate`**: quyền xóa dữ liệu không được phụ thuộc đồng ý nào (người đã rút hết vẫn phải xóa được; nếu cổng chặn thì rút đồng ý sẽ khóa luôn đường xóa). Tin báo là việc RIÊNG và vẫn bị cổng: kiểm khi nhận yêu cầu và kiểm lại lúc gửi (037 FR-002).
- Lưu ý vận hành: job `notify_guardian` chưa chạy trước khi purge chạy (worker tắt > 2 phút) sẽ bị purge xóa cùng job của gia đình ⇒ tin không đi; người giám hộ vẫn thấy gia đình ngừng nhắn. Hạn mức 3/ngày đếm trong bộ nhớ (ADR-002, một tiến trình).
