# Quy trình thí điểm & diễn tập

> **BẢN NHÁP — chờ Minh duyệt** (spec 011, 18/10/2026). Chưa được dùng với người tham gia thật. Chỗ ghi `[CHỜ MINH ĐIỀN]`
> là thông tin chỉ Minh có (số liên hệ, người phụ trách); không ai khác được tự điền. Đạo đức: không gây hoảng sợ, có đồng ý,
> rút lui được bất cứ lúc nào.

## 1. Ai được tham gia
- **Chỉ người ≥ 18 tuổi**, cả người cao tuổi lẫn người giám hộ (CLAUDE.md luật 8). Hỏi tuổi bằng lời trước khi cài; không tham gia nếu không chắc.
- Gia đình có người ≥ 60 tuổi dùng Android và ít nhất 1 người giám hộ dùng Zalo.
- Mỗi người tự đồng ý cho chính mình; không ai đồng ý thay người khác (kể cả con cho cha mẹ).

## 2. Tuyển & cài đặt
- Cài qua Play closed testing (ADR-005), hướng dẫn qua video call có hình minh họa; ghi thời gian onboarding.
- Trước khi cài, đội đọc to và giải thích các văn bản đồng ý trong `docs/legal/consent/` (mỗi mục đích một văn bản, có phiên bản và sha256).
  Người tham gia xem đủ chữ rồi mới bấm đồng ý trên app; bản ghi vào sổ `consents` kèm phiên bản và sha256 của đúng chữ đã đọc.
- Mục đích cần cho thí điểm: `core_protection`, `call_screening`, `usage_monitoring`, `overlay_pause`, `guardian_alerts`,
  `pilot_research`, `drills`; `lookups` hỏi đúng lúc khi dùng lần đầu. `llm_processing` và `voice_input` chỉ khi máy chủ/app đã thực thi (xem DPIA).
- Từ chối một mục đích không làm mất quyền tham gia các phần còn lại, trừ phần phụ thuộc trực tiếp vào nó.

## 3. Diễn tập
- Chỉ trong **khung giờ đã đồng ý**, tối đa **2 lần/tháng**/gia đình (tháng theo giờ Việt Nam; máy chủ từ chối lên lịch lần thứ 3).
- Tên cơ quan và số điện thoại đều **hư cấu**; cờ `is_drill` ở mọi nơi; màu riêng; màn kết thúc "ĐÂY LÀ DIỄN TẬP". Máy chủ chỉ
  tin cờ diễn tập khi khớp một bài đang chạy của đúng người đó, trong khung giờ; ngoài ra coi là sự cố thật.
- Lên lịch và hủy bằng `python -m hoicon.ops.drills schedule|list|cancel` (ngoài dev cần `--confirm`; kịch bản chưa duyệt bị từ chối).
- Người cao tuổi có thể từ chối hoặc dừng bất cứ lúc nào; từ chối không bị coi là "trượt".
- **debrief** ngay sau đó: người giám hộ gọi lại, khen điều làm đúng, nhắc các dấu hiệu lừa đảo của kịch bản. Tin tổng kết gửi người giám hộ qua Zalo có nhãn [DIỄN TẬP] và mở đầu "Đây là trợ lý AI HỏiCon".
- Dừng ngay nếu người tham gia tỏ ra lo âu hoặc bối rối; ghi sự cố đạo đức (xem mục 7).

## 4. Quyền rút lui và xóa dữ liệu
- **Rút lui bất cứ lúc nào**, không cần nêu lý do: tắt quyền trong Cài đặt điện thoại (HỏiCon thôi canh chừng). **Từ spec 032, nếu quyền bị tắt hoặc điện thoại im lặng hơn 24 giờ thì HỏiCon nhắn Zalo cho người giám hộ** (một tin mỗi đợt, không gửi 21:00–07:00; tắt được bằng cờ `HOICON_PROTECTION_WATCH` nếu Minh bác ý I4); nói rõ điều này với người tham gia khi giải thích rút lui,
  hoặc nhờ đội. Rút đồng ý `core_protection` thì máy chủ thôi nhận sự kiện từ máy đó.
- **Yêu cầu xóa dữ liệu**: nói với đội qua kênh hỗ trợ. Đội chạy `python -m hoicon.ops.data request-delete --family <id>` (ghi vết trong `data_requests`),
  mục tiêu hoàn tất trong 72 giờ. Xóa mọi dữ liệu nhận diện của gia đình; sổ đồng ý được giữ nhưng không còn định danh.
- Nói thật với người tham gia: **bản sao lưu cũ** còn chứa dữ liệu của họ tối đa khoảng 4 tuần cho tới khi xoay vòng đẩy đi (`docs/setup/BACKUP.md`).
- Xóa thiết bị bị mất: `python -m hoicon.ops.devices revoke --device <id>`.

## 5. Kênh hỗ trợ
- Người phụ trách thí điểm: `[CHỜ MINH ĐIỀN: tên, vai trò]`.
- Số/Zalo/email hỗ trợ người tham gia: `[CHỜ MINH ĐIỀN]`. Giờ hỗ trợ: `[CHỜ MINH ĐIỀN]`.
- Khi nghi bị lừa thật: bảo người tham gia gọi người thân và ngân hàng của họ trước; HỏiCon không thay thế cơ quan chức năng và không hứa lấy lại tiền.
- Ghi mọi yêu cầu hỗ trợ không kèm số điện thoại, tài khoản hay tên thật.

## 6. Số liệu thu (chỉ tuyên bố số có đo)
Kích hoạt · thời gian onboarding · quyền còn giữ sau 7/14 ngày · tỷ lệ phát hiện khi diễn tập · tỷ lệ vượt qua · thời gian phản hồi
người giám hộ · báo nhầm theo gia đình-tuần · heartbeat · crash-free (Play vitals, ghi cỡ mẫu). Báo cáo bằng `python -m hoicon.ops.pilot
report --days N --json` và `gate-m2` (đầu ra không chứa danh tính); ghi nguồn và cỡ mẫu cạnh mỗi số.

## 7. Điều kiện dừng và sự cố đạo đức
- Dừng toàn bộ thí điểm của một gia đình ngay nếu: người tham gia rút lui, tỏ ra hoảng sợ kéo dài, hoặc phát hiện người chưa đủ 18 tuổi.
- Ghi sự cố đạo đức (không có danh tính), báo Minh trong ngày; không tiếp tục diễn tập với gia đình đó cho tới khi Minh cho phép.
- Nghi ngờ rò rỉ dữ liệu: dừng nạp bản mới, báo Minh, xem `docs/PRIVACY-DPIA.md` mục "Rủi ro & biện pháp".

## 8. Gate
M2 ≥ 5 gia đình (≥ 1 máy thật) · M3 ≥ 20 gia đình, ≥ 20 buổi diễn tập · G3 ≥ 30 gia đình, ≥ 50 buổi diễn tập.
