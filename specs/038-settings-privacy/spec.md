# Spec 038: Cài đặt & quyền riêng tư (E12) — rút đồng ý, xóa dữ liệu từ app

**Nguồn:** PRD US-09 ("Là mẹ, tôi rút đồng ý / xóa dữ liệu bất cứ lúc nào"), DESIGN-SYSTEM E12, ROADMAP P2-20. Lỗ hổng do làn A
phát hiện (GAP-REPORT 23/10): E12 không spec nào sở hữu. Soạn 25/10/2026 (nhà điều phối). Chế độ: tự hành một mạch.

## 1. Hiện trạng (đã đọc mã)
- Đồng ý gắn với quyền hệ thống (`call_screening`, `usage_monitoring`, `overlay_pause`, …): tắt quyền trong Cài đặt ⇒ `ConsentLedger.changes`
  ghi `granted=false` lên `POST /v1/consents` ⇒ máy chủ ép ở mọi đường gửi (034, 037). **Đã chạy.**
- Đồng ý **không** gắn quyền (`guardian_alerts`, `llm_processing`, `drills`, `pilot_research`, `lookups`, `voice_input`): app **không có chỗ rút**.
- Xóa dữ liệu: chỉ có lệnh vận hành `ops.data request-delete` (034). Bảng `data_requests` đã cho `requested_via IN ('ops','app','web')`
  nhưng chưa có API. Màn E12 chưa có; E6 có nút phụ "Xem các quyền" ⇒ `PermissionsScreen`.

## 2. Yêu cầu
- **(FR-001)** *[A]* E12 = mở rộng `PermissionsScreen` (đi từ nút "Xem các quyền" của E6, không thêm nút ở E6): mỗi mục đích một thẻ (tên + một câu
  "dùng để làm gì" lấy từ văn bản đồng ý đã có + trạng thái "● Đang bật" / "○ Chưa bật"). Mục gắn quyền ⇒ nút "Mở cài đặt để tắt" (011 T023).
  Mục không gắn quyền ⇒ nút "Tắt" ⇒ màn xác nhận ("Tắt …? HỏiCon sẽ không … nữa." + "Đúng, tắt" / "Quay lại") ⇒ ghi `granted=false`
  (đường `ConsentLedger` + outbox có sẵn, không đường mạng mới). Bật lại ⇒ đi lại màn đồng ý của mục đó (020/028).
  `core_protection` không có nút tắt riêng: muốn dừng hẳn ⇒ FR-003.
- **(FR-002)** *[A]* Tắt một mục **không bao giờ** tắt dừng an toàn tất định (luật 4): `overlay_pause`/`call_screening` tắt ⇒ E6 khung hổ phách như hiện tại.
- **(FR-003)** *[A + B-api]* "Xóa dữ liệu của gia đình": nút cuối E12 (màu trung tính, không phải màu rủi ro) ⇒ màn giải thích (xóa gì, giữ gì: sổ đồng ý
  giữ theo luật — DATA-MODEL §6; ≤ 72 giờ; con cháu được báo một tin **nếu** bác còn bật `guardian_alerts`) ⇒ **giữ 3 giây** để xác nhận (cùng mẫu nút "tiếp tục" của E7) ⇒
  `POST /v1/data-requests` (thân `data_request.v1`) ⇒ máy chủ ghi `data_requests(kind='delete', requested_via='app')` + xếp `purge_family`
  (dùng lại 034) ⇒ app xóa token + dữ liệu cục bộ (Room, outbox, DataStore) ⇒ về E1 với câu "Đã gửi yêu cầu xóa. Xong trong 72 giờ."
- **(FR-004)** *[B-api]* `POST /v1/data-requests`: xác thực thiết bị; chỉ thiết bị của người được bảo vệ (`role='protected'`); lũy đẳng (yêu cầu
  `pending` đang có ⇒ trả lại nó, 200); hạn mức 3/ngày/thiết bị; được phép **cả khi đã rút đồng ý** (không qua `consent_gate`). Một tin Zalo
  cho người giám hộ hạng 1 qua `messages_out` **chỉ khi `guardian_alerts` còn hiệu lực** (đồng ý lúc gửi — 037 FR-002; đã rút ⇒ không gửi gì) (mẫu soạn sẵn, mở đầu "Đây là trợ lý AI HỏiCon", luật 6), gửi **trước** khi purge xóa kênh.
- **(FR-005)** *[A]* Chữ tiếng Việt ấm áp, không gây hoảng sợ; E12 dùng được ở chữ 200%; mỗi màn ≤ 2 hành động chính; `ux-elder-reviewer` 0 Chặn/Cao.

- **(FR-006)** *[B-api + A]* **Khoảng chờ 24 giờ có thể hủy** (quyết định nhà điều phối 25/10/2026, rà soát Medium #2: kẻ gian có thể dụ bác
  "bấm xóa" để tắt bảo vệ): `POST` ghi `execute_after = now + 24 giờ`, xếp `purge_family` với `run_at = execute_after`; trong khoảng chờ app và máy chủ
  **vẫn bảo vệ bình thường**, E12 hiện "Sẽ xóa lúc {giờ, ngày}" + nút "Hủy yêu cầu xóa" ⇒ `DELETE /v1/data-requests/{id}` ⇒ `cancelled`, job purge bị bỏ.
  Tin báo người giám hộ (nếu còn `guardian_alerts`) gửi ngay lúc yêu cầu, ghi rõ giờ xóa và "nếu bác không muốn, nhắc bác bấm Hủy". App **chỉ xóa dữ
  liệu cục bộ khi máy chủ đã purge** (token bị từ chối 401 sau `execute_after`) — thay cho xóa ngay ở FR-003. Tổng thời gian vẫn ≤ 72 giờ.
  Phạm vi "chỉ xóa phần người yêu cầu khi nhà có ≥ 2 người được bảo vệ" ⇒ chờ Minh (MASTER-PLAN §8 mục 17).

## 3. Tiêu chí thành công
- **(SC-001)** FR-001: tắt từng mục không gắn quyền ⇒ 1 bản ghi `granted=false` tới máy chủ; đường gửi của mục đó dừng (test máy chủ của 037 đã phủ).
- **(SC-002)** FR-003/FR-004: từ E12 tới `data_requests.status='done'` trên máy ảo + backend dev; app về E1, token bị thu hồi (403/401 sau đó).
- **(SC-003)** FR-002: tắt `overlay_pause` rồi chạy `fake_police` ⇒ dừng an toàn vẫn theo hành vi hiện tại (không hồi quy luật 4).
- **(SC-004)** FR-005: reviewer 0 Chặn/Cao; ảnh 100/200%.

## 4. Ngoài phạm vi
Xóa từ web người giám hộ (`requested_via='web'`) — chỉ khi Minh yêu cầu. Xuất dữ liệu (quyền truy cập) — ghi ROADMAP "Ghi chú".
