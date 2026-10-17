# Đánh giá tác động xử lý dữ liệu cá nhân (DPIA rút gọn)

> Trạng thái: **khung** (P0-05) — hoàn thiện ở P1-06, trước khi thí điểm. Căn cứ: Luật Bảo vệ dữ liệu cá nhân
> 91/2025/QH15, Nghị định 356/2025, Nghị định 330/2026 (xử phạt thiếu nhật ký đồng ý), Luật Trí tuệ nhân tạo 134/2025/QH15.

## Cần điền
1. Mô tả xử lý: dữ liệu nào, mục đích (enum `consents.purpose`), cơ sở pháp lý (đồng ý), hạn lưu (DATA-MODEL §6).
2. Luồng dữ liệu: máy → máy chủ (VN/VPS) → nhà cung cấp LLM (nước ngoài: **chỉ dữ liệu đã che PII**, gói trả phí không
   dùng để huấn luyện) → Zalo.
3. Dữ liệu nhạy cảm: không thu nội dung cuộc gọi/SMS/danh bạ; số điện thoại chỉ ở dạng băm (ADR-006).
   - `CallScreeningService` được gọi cho cả cuộc gọi **đến và đi** tới số không có trong danh bạ ⇒ DPIA phải ghi cả
     hai chiều (review bảo mật 09/10).
   - `h1` là SHA-256 không muối trên không gian ~10⁹ số ⇒ coi là **dữ liệu cá nhân đã bí danh hóa**, không phải ẩn
     danh; lưu trên máy phải mã hóa (Room + Tink AEAD, P2-05), không để trong SharedPreferences dạng rõ như bản spike.
   - Log chẩn đoán (tên gói ngân hàng + 3 số cuối + mức rủi ro) chỉ có ở bản debug.
4. Quyền chủ thể: xem, rút đồng ý (E12), xóa/xuất (`data_requests`), thời hạn phản hồi.
5. Rủi ro & biện pháp: rò rỉ DB, prompt injection, báo nhầm gây hoảng, lạm dụng diễn tập, người giám hộ lạm quyền.
6. Công khai AI: "Đây là trợ lý AI HỏiCon" + trang `/ai`.
7. Thí điểm: chỉ người ≥ 18 tuổi; văn bản đồng ý có phiên bản (`docs/legal/consent/`).

## Quy trình vận hành đã cài đặt (spec 034 — gia cố lõi)
Phần này ghi cái ĐÃ chạy được và kiểm bằng test; những gì phụ thuộc VPS/lịch chạy (spec 012) ghi rõ là chưa.

### Hạn lưu tự động
Job `retention` chạy mỗi ngày (khóa `retention:<ngày giờ VN>`), theo lô ≤ 1.000 dòng, lũy đẳng; `python -m hoicon.ops.data
retention --dry-run` in số dòng sẽ bị đụng. Bảng hạn lưu là DATA-MODEL §6 (test so khớp hằng số `RETENTION` với bảng đó).
`consents` không bao giờ bị đụng. Toàn văn tin gửi người giám hộ nằm trong `jobs.payload` nên bị xóa sau 30 ngày kể từ
khi job xong; `messages_out` không có cột văn bản và được giữ để đếm hạn mức Zalo.

### Xóa dữ liệu theo yêu cầu (US-09 / US-20.2)
1. Người dùng yêu cầu qua đội thí điểm (chưa có màn trên app: spec riêng sau; `requested_via` đã dự phòng `app`, `web`).
2. Đội chạy `python -m hoicon.ops.data request-delete --family <id>` (ngoài dev cần `--confirm`): ghi `data_requests`
   (`pending`) và xếp job `purge_family`. Mục tiêu hoàn tất ≤ 72 giờ; `status --request <id>` xem trạng thái.
3. Job: thu hồi thiết bị trước; xóa checkpoint đồ thị; xóa sự cố, sự kiện rủi ro, bước tác tử, job, tin gửi đi, token
   hành động, liên hệ tin cậy, mã ghép, xác minh, diễn tập, thiết bị; ẩn danh `members` (bí danh `[đã xóa]`, HMAC Zalo và
   bản mã định danh = NULL) và `families`. **Giữ nguyên `consents`** (Nghị định 356/2025): chỉ còn mục đích, đồng ý hay
   không, băm văn bản đồng ý và thời điểm; không còn định danh. `data_requests` giữ làm vết (không có văn bản tự do).
4. Token thiết bị/người giám hộ cũ bị từ chối ngay (401). Lỗi giữa chừng ⇒ yêu cầu `failed` kèm mã lỗi ngắn, job thử lại.
5. Chưa làm: xuất dữ liệu (`kind=export`), màn E12 trên app.

### Sao lưu
`docs/setup/BACKUP.md`. Bản sao lưu chứa dữ liệu cá nhân nên luôn mã hóa AES-256-GCM (khóa `HOICON_BACKUP_KEY_<kid>` riêng,
khác khóa dữ liệu) trước khi rời container; bản rõ không chạm đĩa. **Sau khi một gia đình bị xóa, bản sao lưu cũ vẫn chứa dữ
liệu của họ cho tới khi xoay vòng đẩy nó đi (tối đa ~4 tuần: 7 bản ngày + 4 bản tuần)** — phải nêu rõ điều này trong văn
bản đồng ý/chính sách khi thí điểm; không khôi phục bản cũ vào hệ thống đang chạy mà không chạy lại các yêu cầu xóa.

### Đồng ý được thực thi ở máy chủ
Rút `core_protection` ⇒ `POST /v1/events` trả 403 `consent_withdrawn` và không ghi gì. Thiếu `guardian_alerts` ⇒ vẫn nhận
sự kiện (an toàn người cao tuổi) nhưng không có tin Zalo nào tới người giám hộ. Trễ tối đa 60 giây (đệm) nếu đồng ý đổi từ
kênh khác ngoài `/v1/consents`.

### Gỡ cờ một số điện thoại bị gắn nhầm
1. Người bị gắn nhầm (hoặc người giám hộ) báo cho đội; đội xác minh bằng chứng ngoài hệ thống.
2. Lấy `h1` của số đó (SHA-256 của `"hoicon:v1:" + E.164`) ở máy đội, ghi vào tệp tạm, mỗi dòng một h1 (không bao giờ ghi
   số thô vào tệp hay ticket).
3. `python -m hoicon.ops.threat_list unflag --h1-file <tệp> [--confirm]` — gỡ theo HMAC với mọi kid pepper, in số đã gỡ/không
   thấy, không in h1; một dòng sai định dạng ⇒ từ chối cả tệp. Xóa tệp tạm.
4. Máy giữ ảnh chụp danh sách cũ tới lần đồng bộ kế tiếp (bucket chỉ để lọc sơ bộ, kết luận cuối vẫn do máy chủ tra).

### Thu hồi thiết bị bị mất
`python -m hoicon.ops.devices revoke --device <id>`: token cũ bị từ chối ngay ở yêu cầu kế tiếp, không chờ hết hạn.

### Tách role CSDL
`infra/postgres/roles.sql`: role `hoicon_app` không sở hữu bảng, chỉ `SELECT`/`INSERT` trên `consents` và
`incident_transitions`, không tắt được trigger bất biến (kiểm bằng quyền, không chỉ bằng trigger). Áp dụng ở prod thuộc 012.
