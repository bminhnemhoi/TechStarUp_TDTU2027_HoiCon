# Plan 038 — Cài đặt & quyền riêng tư

- **D1** Không màn mới cho danh sách: mở rộng `PermissionsScreen.kt` (đã là đích của "Xem các quyền"); thêm `PrivacyDeleteScreen.kt` (giải thích + giữ 3 giây).
- **D2** Tắt mục không gắn quyền dùng đúng `ConsentLedger` + outbox `POST /v1/consents` (không API mới) ⇒ hoạt động khi offline, gửi khi có mạng.
- **D3** Xóa dữ liệu cần mạng (máy chủ phải ghi). Offline ⇒ "Chưa gửi được, bác thử lại khi có mạng" — **không** xóa cục bộ trước khi máy chủ nhận
  (tránh trạng thái app trống mà dữ liệu máy chủ còn).
- **D4** `POST /v1/data-requests` đi sau xác thực thiết bị nhưng **trước** `consent_gate`; gọi `purge_service` qua job có sẵn; tin báo người giám hộ xếp
  với ưu tiên cao hơn `purge_family` (cùng giao dịch, thứ tự job). Hợp đồng `docs/schemas/data_request.v1.json` (kiến trúc sư, làm trước).
- **D5** Sau 202/200: app xóa `token`, Room, DataStore, outbox; huỷ worker; về E1. Mã lỗi 403 `consent_withdrawn` không áp dụng cho route này.
- **D6** (25/10) Khoảng chờ 24 giờ: cột `data_requests.execute_after` + trạng thái `cancelled` (migration mới, làn B); `purge_family` kiểm lại trạng thái lúc chạy (đã `cancelled` ⇒ thoát). D5 đổi: app không xóa cục bộ ngay mà chờ 401 sau `execute_after`.
