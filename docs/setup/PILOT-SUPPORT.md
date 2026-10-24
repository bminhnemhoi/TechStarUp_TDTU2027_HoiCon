# Hỗ trợ gia đình thí điểm

> **BẢN NHÁP — chờ Minh duyệt bản cuối** (spec 029 T009, 24/10/2026). Dành cho người trực hỗ trợ của đội. Đi kèm
> `docs/PILOT-PROTOCOL.md` (đạo đức, quyền rút lui) và `docs/setup/PILOT-ONBOARDING.md` (cài đặt). Chỗ `[CHỜ MINH ĐIỀN]` là thông tin
> chỉ Minh có (số liên hệ, người phụ trách, giờ trực); không ai khác tự điền.

## Nguyên tắc chung
- Nói chuyện ấm áp, không đổ lỗi, không làm hoảng sợ; xưng hô theo người đối diện. Việc cụ thể kế tiếp luôn đi kèm câu trả lời.
- **Ghi yêu cầu hỗ trợ không kèm số điện thoại, số tài khoản, Zalo ID hay tên thật** (luật 1). Chỉ dùng mã gia đình/thiết bị của máy chủ (biệt danh như "Mẹ" có thể nhận ra người khi có ít gia đình).
- Người tham gia **dừng được bất cứ lúc nào**. Có yêu cầu rút lui hay xóa dữ liệu thì làm ngay, không hỏi lý do, không thuyết phục.
- HỏiCon không thay cơ quan chức năng và không hứa lấy lại tiền. Nghi bị lừa thật: nói "Bác ngồi xuống, hít thở. Chưa mất gì thì cứ dừng ở đó. Bác gọi số in sau thẻ ngân hàng (đừng gọi số người lạ vừa đưa) và gọi con ngay nhé."
- Phải có **số điện thoại** (người cao tuổi chưa chắc dùng Zalo). Số liên hệ hỗ trợ người tham gia: `[CHỜ MINH ĐIỀN]` · giờ trực: `[CHỜ MINH ĐIỀN]` · người phụ trách: `[CHỜ MINH ĐIỀN]`.
- **Khẩn** (nghi người tham gia đang bị lừa, hoặc đang hoảng sợ kéo dài): ưu tiên cao nhất; bảo họ gọi người thân/ngân hàng, rồi báo
  Minh **trong ngày** (xem mục 6).

Lệnh vận hành dưới đây chạy bằng `uv run --directory backend python -m …` trên máy có quyền vào DB (ngoài dev cần `--confirm` ở
lệnh ghi). Không in danh tính; kết quả chỉ có mã và số.

## 1. "Mất bảo vệ" (heartbeat dừng hoặc quyền bị tắt)
**Dấu hiệu:** người giám hộ nhận tin Zalo từ HỏiCon (spec 032) dạng "Điện thoại của … chưa báo về HỏiCon từ …" hoặc "quyền để HỏiCon
nhắc dừng lại … đang bị tắt". Máy chủ gửi **một** tin cho mỗi thiết bị trong 24 giờ, **không** gửi 21:00–07:00 giờ Việt Nam (xếp lại
lúc 07:00), và đặt "im lặng" khi hơn **24 giờ** không có heartbeat.

| Nguyên nhân thường gặp | Việc làm |
|---|---|
| Máy hết pin, tắt máy, mất mạng | Người giám hộ gọi hỏi thăm; khi máy bật lại, HỏiCon tự báo lại. Không cần can thiệp. |
| Hệ thống tắt app nền (tiết kiệm pin theo hãng) | Hướng dẫn lại bước "Không giới hạn pin" (`PILOT-ONBOARDING.md` mục 3). **Ghi hãng/máy/bản Android** để đối chiếu; chưa kết luận mức tương thích cho tới khi đo trên máy thật. |
| Quyền bị tắt (người cao tuổi hoặc bản cập nhật hệ điều hành) | **Hỏi trước, nhẹ nhàng**: "Bác tắt vì không muốn dùng nữa, hay lỡ tay ạ?" Nếu không muốn dùng nữa ⇒ sang mục 3, **không xin bật lại**. Nếu lỡ tay ⇒ nhờ bác mở HỏiCon: màn chính hiện khung hổ phách "Còn thiếu một bước", bấm "Bật mục còn thiếu". |
| Thiết bị bị mất / thu hồi | `python -m hoicon.ops.devices revoke --device <id> --confirm`. Thiết bị thu hồi **không** còn gửi cảnh báo. |
| Người cao tuổi đã rút đồng ý `core_protection` | Đúng thiết kế: máy chủ thôi nhận sự kiện của máy đó. **Không** xin họ bật lại; ghi nhận và cảm ơn. |

Kiểm tra từ máy chủ (không danh tính): `python -m hoicon.ops.pilot report --days 7 --json` cho độ phủ heartbeat và quyền tắt theo gia đình.
Tắt mọi cảnh báo "mất bảo vệ" khi cần: cờ `HOICON_PROTECTION_WATCH=false` (quyết định của Minh, `PILOT-PROTOCOL.md` mục 4); nói rõ
việc này với người tham gia vì họ đã được nghe rằng người giám hộ sẽ được báo.

## 2. Báo nhầm (HỏiCon nhắc nhưng thực ra việc bình thường)
- Trấn an trước: "Cảm ơn bác đã cho biết, bác nói giúp đội chỉnh lại cho đúng. Bác cứ làm tiếp việc bác cần."
- Người cao tuổi **vẫn tiếp tục được**: nút "Vẫn tiếp tục" cần giữ 3 giây và kết quả được ghi lại; app không bao giờ khóa vĩnh viễn.
- Người giám hộ chọn **"An toàn"** ở trang hành động của sự cố để đóng sự cố; lựa chọn này
  được tính vào số liệu "báo nhầm theo gia đình-tuần".
- Ghi: **ứng dụng nào và tình huống nào** (không ghi nội dung cuộc gọi, số điện thoại, tên). Gửi cho đội để chỉnh luật; **không** tự ý hạ
  mức rủi ro (luật tất định trên máy là mức sàn, LLM chỉ nâng, không hạ).
- Nếu cùng một gia đình báo nhầm liên tục, hỏi ý họ có muốn tiếp tục không.

## 3. Gỡ cài đặt (người dùng muốn thôi)
1. Xác nhận bằng lời: "Bác muốn dừng HỏiCon đúng không ạ?" Không hỏi lý do; cảm ơn.
2. Hướng dẫn gỡ ứng dụng trong Cài đặt điện thoại. **Gỡ app chưa xóa dữ liệu đã gửi lên máy chủ**: hỏi người đó có muốn **xóa dữ liệu** luôn không (mục 4).
3. Máy chủ phát hiện máy im lặng hơn 24 giờ ⇒ người giám hộ **sẽ nhận một tin** "chưa báo về HỏiCon" (người cao tuổi đã được báo trước điều này lúc cài). **Hỏi người cao tuổi trước**: "Con có nói với con bác là bác đã dừng được không ạ?" Chỉ báo người giám hộ khi họ đồng ý; nếu không thì thu hồi thiết bị (mục 1) để máy chủ thôi gửi tin.
4. Ghi nhận "đã rút lui" (không danh tính) và dừng diễn tập với gia đình đó.

## 4. Yêu cầu xóa dữ liệu
- Người tham gia nói với đội qua kênh hỗ trợ; **mục tiêu hoàn tất trong 72 giờ**.
- Chạy: `python -m hoicon.ops.data request-delete --family <id> --confirm` (ghi vết vào `data_requests`; thêm `--now` nếu cần thi
  hành ngay thay vì chờ worker). Xem trạng thái: `python -m hoicon.ops.data status --request <id>`.
- Xóa mọi dữ liệu nhận diện của gia đình; **sổ đồng ý được giữ nhưng không còn định danh**.
- Nói rõ: mục tiêu là hoàn tất trong 72 giờ (không phải cam kết tuyệt đối) và đội sẽ báo lại khi xong.
- **Nói thật** với người yêu cầu: **bản sao lưu cũ** còn chứa dữ liệu của họ tối đa khoảng **4 tuần** cho tới khi xoay vòng đẩy đi
  (`docs/setup/BACKUP.md`); nếu khôi phục từ bản sao lưu thì đội sẽ xóa lại theo danh sách yêu cầu xóa (lệnh `ops backup restore` in nhắc).
- Thiết bị đã mất: `python -m hoicon.ops.devices revoke --device <id> --confirm`.
- Đồng ý từng mục đích rút được riêng (không cần xóa hết): qua màn E12 Cài đặt & quyền riêng tư của app (kiểm lại màn này đã làm xong chưa trước khi hứa với người tham gia).

## 5. Người giám hộ không vào được web
- Nhắn **số 4** cho HỏiCon trên Zalo để nhận liên kết đăng nhập mới (dùng một lần, hết hạn 15 phút; xin nhiều quá trong một giờ thì phải chờ).
- Dặn: chỉ mở trên máy của mình, không chuyển tiếp liên kết.
- Mở được nhưng không thấy sự cố: kiểm tra gia đình có sự cố thật nào chưa; sự cố mô phỏng của gian trưng bày **không** hiện cho gia đình thật.

## 6. Khi cần báo Minh (trong ngày)
Báo ngay (không kèm danh tính) nếu: người tham gia tỏ ra hoảng sợ hoặc lo âu kéo dài, rút lui giữa chừng sau diễn tập; phát hiện người
**chưa đủ 18 tuổi**; nghi rò rỉ dữ liệu; hoặc người tham gia nói đã bị lừa thật. Ghi **sự cố đạo đức** theo `PILOT-PROTOCOL.md` mục 7 và
**không** tiếp tục diễn tập với gia đình đó cho tới khi Minh cho phép.

## 7. Sổ hỗ trợ (mẫu một dòng, không danh tính)
`ngày · mã gia đình · loại (mất bảo vệ / báo nhầm / gỡ / xóa / web / khác) · hãng-máy-bản Android (nếu liên quan) · đã làm gì · đã xong chưa`.
Không ghi số điện thoại, tài khoản, tên thật, nội dung cuộc gọi. Đây là nguồn cho số liệu "báo nhầm theo gia đình-tuần" và "quyền còn
giữ sau 7/14 ngày"; mỗi số ghi nguồn và cỡ mẫu.
