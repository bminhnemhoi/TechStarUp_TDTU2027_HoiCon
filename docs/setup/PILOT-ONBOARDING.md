# Hướng dẫn cài đặt cho gia đình thí điểm (video call, khoảng 15–20 phút)

> **BẢN NHÁP — chờ Minh duyệt bản cuối** (spec 029 T009, 24/10/2026). Chưa dùng với người tham gia thật. Đi kèm
> `docs/PILOT-PROTOCOL.md` (quy trình, đạo đức) và `docs/setup/PILOT-SUPPORT.md` (khi có vấn đề). Chỗ ghi `[CHỜ MINH ĐIỀN]`
> là thông tin chỉ Minh có. Chỗ ghi **[CHƯA KIỂM TRÊN MÁY THẬT]** là đường đi trong cài đặt mỗi hãng: tên mục có thể khác theo
> bản Android và bản giao diện; người hướng dẫn nhìn màn hình thật rồi chỉnh lại cho đúng, và ghi lại cho đội.

Người hướng dẫn là thành viên đội HỏiCon. Cả buổi nói chậm, xưng "bác/cô/chú" theo người đối diện, **không giục**; nghỉ bất cứ lúc nào người đó muốn.
Các mốc phút dưới đây chỉ là ước lượng cho đội chuẩn bị, **không phải lời hứa** với gia đình và không đặt áp lực lên người cao tuổi.
App gọi người dùng là "bác" và xưng "con" cố định (chưa chỉnh được): nói trước "Máy sẽ gọi mình là bác cho tiện, cô/chú đừng để ý nhé"; đội ghi nhận cần chỉnh app. Mọi chữ trong
app là tiếng Việt do app tự hiện; người hướng dẫn **không** bấm thay người cao tuổi.

## 0. Trước buổi gọi (đội làm, 5 phút)
1. Hỏi **bằng lời, trước khi cài**: cả người cao tuổi lẫn người giám hộ đều từ **đủ 18 tuổi** trở lên. Không chắc thì **không** tham gia
   (luật 8). Chỉ khi cả hai xác nhận đúng mới ghi danh gia đình:
   `uv run --directory backend python -m hoicon.ops.pilot enroll --family <id> --confirm-adult`
   (lệnh từ chối nếu thiếu `--confirm-adult`). Người ghi danh là người đã hỏi tuổi, không phải người suy đoán.
2. **Cả hai máy** (người giám hộ và người cao tuổi) dùng tài khoản Google đã **tham gia Google Group tester** của HỏiCon và nhận **lời mời Play (closed testing)** (ADR-005);
   app đã được cài sẵn vào máy người cao tuổi trước buổi gọi (người giám hộ hoặc đội làm cùng, không bắt người cao tuổi tự làm một mình). Cách làm: bấm liên kết mời → "Trở thành người thử nghiệm" → cài từ Cửa hàng Play. Hạn duyệt của Google có thể mất vài ngày, nên làm trước
   buổi gọi ít nhất 2 ngày. Link và tên Group: `[CHỜ MINH ĐIỀN]`.
3. Người giám hộ đã có Zalo và đã nhắn HỏiCon trên Zalo (để nhận mã ghép 6 số). Người cao tuổi chưa cần Zalo.
4. Đặt bên cạnh: bản in hoặc ảnh các màn E1–E4 (xem mục 6) để chỉ khi người cao tuổi lạc.
5. Ghi **thời gian từ lúc mở app tới khi E6 hiện "Đang bảo vệ"** chỉ để thống kê onboarding (`docs/PILOT-PROTOCOL.md` mục 6); không đặt mốc cho người hướng dẫn và không nhắc giờ với người cao tuổi.
6. **Đọc to và giải thích các văn bản đồng ý TRƯỚC khi mở app** (đúng `docs/PILOT-PROTOCOL.md` mục 2): để người cao tuổi hiểu rồi mới bắt đầu. Ở bước E3, người đó sẽ tự đọc và tự bấm. Đọc cùng lúc điều này: "Nếu điện thoại bác im lặng hơn một ngày hoặc quyền bị tắt, HỏiCon sẽ nhắn cho con bác biết để con gọi hỏi thăm bác. Nếu bác tắt vì không muốn dùng nữa, bác gọi đội trước, con bác sẽ không bị nhắn báo."
7. **Người giám hộ chưa gửi mã ghép và chưa dùng Zalo/web cho tới khi bước đồng ý của chính họ được Minh chốt và hoàn tất** (mục 5 bước 0).
8. Địa chỉ Gmail của người tham gia chỉ nhập thẳng vào Google Group, **không chép vào sổ** hay chat (luật 1).

## 1. Kịch bản gọi (ước lượng, không giục)

| Phút | Việc | Người cao tuổi thấy |
|---|---|---|
| 0:00 | Chào, nhắc đây là **thử nghiệm**, bác dừng lúc nào cũng được; hỏi lại tuổi nếu chưa hỏi. | — |
| 0:30 | Mở app HỏiCon (đã cài). | **E1 Chào mừng**: câu "Đây là trợ lý AI HỏiCon" |
| 1:00 | Người giám hộ gửi mã 6 số cho người cao tuổi (nhắn tin hoặc Zalo), người cao tuổi gõ vào. Dặn: "Đây là mã kết nối của HỏiCon, chỉ để bác gõ vào máy này. Mã xác thực (OTP) của ngân hàng thì bác không đọc cho ai nghe." Màn E2 ghi "qua Zalo": nói rõ nếu bác không dùng Zalo thì gửi bằng tin nhắn cũng được. | **E2 Ghép đôi**: "Nhập mã kết nối từ con" (chưa gửi nội dung nào lên máy chủ) |
| 1:45 | Người cao tuổi tự đọc cam kết trên màn hình (bản đầy đủ nằm ở `docs/legal/consent/`; app đọc to bản tóm tắt, cho xem bản đầy đủ khi cần), rồi tự bấm "Đồng ý, tiếp tục" hoặc "Chưa đồng ý". | **E3 Công bố & đồng ý** |
| 2:30 | Bật từng quyền theo E4: mỗi quyền một bước, điện thoại sẽ mở hộp hỏi hoặc trang cài đặt. | **E4 Mỗi quyền một bước** ("Bước 1 trên N") |
| 4:00 | Kiểm tra màn kết quả. | **E6 "Đang bảo vệ"** (khiên xanh) hoặc khung hổ phách nếu còn thiếu |
| 4:30 | Dặn: "Có số lạ gọi rồi mở ứng dụng ngân hàng, HỏiCon sẽ nhắc bác dừng lại. Khi HỏiCon nhắc, bác cứ dừng lại và gọi cho con, con sẽ giúp bác xem có đúng không." Cho số hỗ trợ (mục 7). | — |

Nếu màn hình khác với tài liệu: "Máy của bác hiển thị hơi khác, mình tìm một chút nhé." Không tìm được mục nào thì **để E6 hổ phách, không ép**.

Quy tắc khi người cao tuổi bối rối: dừng, nói "không sao bác ạ", cho nghỉ; **không** bấm giúp; nếu người đó muốn thôi, tôn trọng ngay
và ghi nhận (không coi là thất bại). Từ chối một mục đích **không** mất quyền dùng các phần còn lại, trừ phần phụ thuộc trực tiếp
vào nó (`docs/PILOT-PROTOCOL.md` mục 2).

## 2. Đồng ý (E3) — làm đúng thứ tự
- Đã đọc to và giải thích từ trước buổi gọi (mục 0); tại E3, để người cao tuổi **tự đọc** rồi tự bấm. Không ai đồng ý thay người khác, kể cả con cho cha mẹ.
- App ghi bản ghi đồng ý kèm phiên bản và sha256 của đúng chữ đã hiện. Mục đích cần cho thí điểm và mục nào hỏi "đúng lúc": xem
  `docs/PILOT-PROTOCOL.md` mục 2. Nếu người cao tuổi bấm **"Chưa đồng ý"**: app hiện "Không sao bác ạ", HỏiCon chưa gửi gì cho
  con; người hướng dẫn cảm ơn và hẹn lại, không thuyết phục.
- **Từ chối mục nào thì mất gì** (bản nháp, đối chiếu `docs/PILOT-PROTOCOL.md` mục 2; Minh chốt bản cuối). Người hướng dẫn nói đúng như dưới đây và **không thuyết phục**:
  - `core_protection`: nền tảng; từ chối thì chưa dùng được HỏiCon (máy chủ không nhận sự kiện).
  - `call_screening`, `usage_monitoring`, `overlay_pause`: ba mục để nhận ra "số lạ rồi mở app ngân hàng" và hiện lời nhắc; thiếu mục nào thì phần nhắc dừng lại phụ thuộc mục đó **không chạy**, các mục khác vẫn dùng.
  - `guardian_alerts`: thiếu thì con cháu không nhận được tin Zalo.
  - `pilot_research`: thiếu thì **không thu số liệu** của gia đình đó; vẫn dùng bình thường.
  - `drills`: thiếu thì không có diễn tập.
- Phần `llm_processing` và `voice_input` chỉ nhắc khi máy chủ và app đã thực thi (đang chờ spec 011, xem `docs/PILOT-PROTOCOL.md`
  mục 9).

## 3. Các quyền (E4) và "không giới hạn pin"
App xin lần lượt, mỗi quyền một màn, đúng chữ của app: **nhận diện cuộc gọi lạ** (chọn HỏiCon trong hộp hỏi), **biết app nào đang
mở** (trang cài đặt "quyền truy cập dữ liệu sử dụng": bật công tắc của HỏiCon), **hiện nhắc trên màn hình** (hiện lên trên ứng dụng
khác), **thông báo** (bấm Cho phép) và **không giới hạn pin** ("Không tối ưu hóa"). Nếu người cao tuổi chưa muốn bật mục nào thì **mình để đó, HỏiCon vẫn dùng được phần còn lại, không sao ạ**; không ép tới khi hiện khiên xanh. Mục nào chưa bật, người cao tuổi có thể "Để sau"
và bật ở màn chính; HỏiCon sẽ báo "Còn thiếu một bước" cho tới khi đủ. App **không** xin quyền SMS, nhật ký cuộc gọi, danh bạ hay
Trợ năng; nếu hộp hỏi nào xin những quyền đó, **dừng** và nói: "Bác chưa bấm gì cả nhé, mình dừng ở đây. Có thể điện thoại đang mở nhầm ứng dụng khác, đội kiểm tra giúp bác." Rồi báo đội.

"Không giới hạn pin" là bước hay bị bỏ sót nhất và làm HỏiCon bị hệ thống tắt khi nằm nền. Tên và đường đi theo từng hãng
**[CHƯA KIỂM TRÊN MÁY THẬT — người hướng dẫn nhìn màn hình thật rồi chỉnh]**:

| Hãng / giao diện | Gợi ý đường đi | Lưu ý |
|---|---|---|
| Samsung One UI | Cài đặt → Ứng dụng → HỏiCon → Pin → chọn **Không hạn chế** (hoặc "Không giới hạn"). Có thể thêm HỏiCon vào danh sách "Ứng dụng không bao giờ ngủ" ở Chăm sóc thiết bị/Pin. | Tên "Chăm sóc thiết bị" đổi theo bản One UI. |
| Xiaomi HyperOS / MIUI | Cài đặt → Ứng dụng → Quản lý ứng dụng → HỏiCon → **Tiết kiệm pin** → chọn **Không hạn chế**; bật thêm **Tự khởi động** nếu có. | Nếu máy có "ứng dụng kép" / "không gian thứ hai": hỏi người dùng có dùng ngân hàng ở chế độ đó không và **ghi lại** (có thể làm HỏiCon không thấy app đang mở; xem rủi ro RB-6 ở `docs/spikes/P1-S2-dung-an-toan.md`). |
| Oppo ColorOS (cũng Realme, OnePlus) | Cài đặt → Pin → HỏiCon (hoặc "Quản lý mức sử dụng pin") → cho phép **chạy nền / tự khởi động**, chọn không tối ưu. | ColorOS đổi tên mục thường xuyên. |
| Android thuần / hãng khác | Màn E4 của app mở đúng danh sách "Tối ưu hóa pin" của Android: chọn HỏiCon → **Không tối ưu hóa**. | Đây là đường duy nhất app tự mở; các hãng trên chỉ là thêm. |

Sau khi bật, **ghi vào sổ thí điểm** (không kèm tên): model máy, bản Android, hãng, đã bật "không giới hạn pin" chưa. Số này dùng để
đối chiếu với heartbeat (spec 032) và chưa kết luận gì về mức tương thích tới khi đo trên máy thật.

## 4. Kiểm tra "Đang bảo vệ" (E6)
- **Đạt**: nhãn khiên xanh "Đang bảo vệ bác" (E6), nút "Hỏi con" và "Xem các quyền".
- **Chưa đạt**: khung màu hổ phách "Còn thiếu một bước"; nút "Bật mục còn thiếu" đưa tới đúng quyền còn thiếu. Nếu người cao tuổi **muốn** bật thì làm cùng; nếu không thì để vậy (xem mục 3). E6 chỉ phản ánh quyền đã bật, **không chứng minh** máy đang được bảo vệ.
- Kiểm tra từ phía người giám hộ: mở trang web (mục 5 bước 3) hoặc hỏi người giám hộ xem đã thấy tin từ HỏiCon chưa. Máy chủ ghi nhận
  máy "còn sống" qua heartbeat; ngay sau khi ghép, có thể mất vài phút mới thấy.
- **Không** hứa "luôn bảo vệ tuyệt đối". Nói đúng: HỏiCon nhắc bác dừng lại khi thấy dấu hiệu; bác vẫn tự quyết.

## 5. Người giám hộ (làm sau cuộc gọi, có thể làm sau)
0. **Đồng ý của người giám hộ**: người giám hộ cũng đưa dữ liệu (Zalo, đăng nhập web) và phải tự đồng ý cho chính mình, tự rút được (`docs/PILOT-PROTOCOL.md` mục 1). **[CHƯA XÁC ĐỊNH]** bước đồng ý này nằm ở đâu trong luồng hiện có; Minh chốt trước khi dùng với người thật (`PILOT-PROTOCOL.md` mục 9).
1. Nhắn **số 4** cho HỏiCon trên Zalo để nhận **liên kết đăng nhập web** (dùng một lần, hết hạn sau 15 phút).
2. Mở liên kết trên máy của mình (không chuyển tiếp cho ai), xem danh sách sự cố.
3. Mở trang diễn tập `/drills` khi cần xếp lịch (chỉ khi người cao tuổi đã đồng ý mục đích `drills`).
4. Dặn: tin Zalo từ HỏiCon luôn mở đầu bằng "Đây là trợ lý AI HỏiCon"; tin nào không như vậy là **không** phải HỏiCon.

## 6. Ảnh minh họa
Ảnh các màn E1–E4 (100% và 200% cỡ chữ) lấy từ `~/hoicon-evidence/020-family-pairing-consent/shots/` (E1 `e1-welcome-*`, E2 `e2-pairing-*`,
E3 `e3-disclosure-*`, E4 `e4-permission-*`); E6 từ `~/hoicon-evidence/022-sentinel-v1/shots/`. Đó là ảnh **máy ảo**, không phải máy
thật của hãng nào; khi in cho gia đình thì dùng ảnh chụp từ máy thật nếu có. Ảnh không chứa dữ liệu thật (chỉ dữ liệu hư cấu).

## 7. Kết thúc buổi gọi
- Đọc lại, nói chậm: "Bác dừng lúc nào cũng được, không cần nêu lý do. Có ba cách, bác chọn cách nào dễ nhất: (1) tắt quyền trong Cài đặt điện thoại; (2) nói với đội, đội tắt giúp từng mục cho bác ngay (chưa xác nhận app đã có màn tự rút từng mục); (3) nói với con hoặc gọi đội, đội làm giúp bác ngay. Bác muốn xóa dữ liệu thì nói với đội, đội sẽ cố gắng xóa trong vòng 72 giờ và báo lại cho bác khi xong." **Nói thật**: bản sao lưu cũ còn dữ liệu tối đa khoảng 4 tuần.
- Nói trước điều người giám hộ sẽ biết: "Nếu điện thoại bác im lặng hơn một ngày hoặc quyền bị tắt, HỏiCon sẽ nhắn cho con bác biết để con gọi hỏi thăm bác." Người cao tuổi chưa có Zalo vẫn dùng được; cho họ **số điện thoại hỗ trợ** để gọi trực tiếp.
- Cho số/Zalo hỗ trợ và giờ hỗ trợ: `[CHỜ MINH ĐIỀN]` (xem `PILOT-SUPPORT.md`). **Phải có số điện thoại** (người cao tuổi chưa chắc dùng Zalo): đọc to rồi viết lớn cho họ. Chưa có số thì chưa chạy buổi nào. Không ghi số điện thoại, tài khoản hay tên thật vào sổ.
- Khi nghi bị lừa thật: bảo bác gọi người thân và ngân hàng của chính bác trước; HỏiCon không thay cơ quan chức năng và không hứa lấy lại tiền.
- Điền sổ: thời gian onboarding, máy/hãng/bản Android, quyền nào còn thiếu. Không ghi danh tính.
