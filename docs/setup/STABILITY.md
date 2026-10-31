# Đo độ ổn định của app Android bằng Android vitals (spec 037 FR-008, T015)

**Quyết định hiện hành:** chưa dùng Crashlytics (cần SDK, mục đích đồng ý mới và khai báo data safety — luật 7; MASTER-PLAN §8
mục 13 chờ Minh). Độ ổn định đo bằng **Android vitals** trong Play Console: dữ liệu do Google thu từ máy người dùng đã bật chia
sẻ, HỏiCon không thu thêm gì và không cần mục đích đồng ý mới. SC-006 (crash-free ≥ 99% trên máy thật) **chưa đo** tới khi có
Play Console và bản phát hành (W0-3); không được ghi con số trước đó.

## Đọc ở đâu
Play Console → ứng dụng → **Chất lượng ứng dụng (Quality) → Android vitals → Tổng quan**. Hai chỉ số chính:
- **Tỷ lệ gặp sự cố người dùng cảm nhận được** (user-perceived crash rate): % người dùng hoạt động hằng ngày gặp ít nhất một
  lần ứng dụng đóng đột ngột khi đang dùng. **Crash-free = 100% − tỷ lệ này.**
- **Tỷ lệ ANR người dùng cảm nhận được** (user-perceived ANR rate): % người dùng gặp "ứng dụng không phản hồi".
Chọn khoảng **28 ngày** (đúng cách Play đánh giá); có thể lọc theo phiên bản, kiểu máy, hãng, bản Android. Mục **Sự cố và ANR
(Crashes and ANRs)** liệt kê cụm lỗi theo dấu vết ngăn xếp — dùng để tìm nguyên nhân, không để đếm người.

## Ngưỡng "hành vi xấu" của Play
Theo tài liệu Play Console tại thời điểm viết (**kiểm lại trên trang trợ giúp của Google trước khi dùng; ngưỡng có thể đổi**):
- Tổng thể: tỷ lệ sự cố người dùng cảm nhận được **≥ 1,09%** hoặc tỷ lệ ANR **≥ 0,47%** (28 ngày) là vượt ngưỡng xấu.
- Theo từng kiểu máy: **≥ 8%** cho cả hai chỉ số trên một kiểu máy là vượt ngưỡng xấu riêng của kiểu máy đó.
Vượt ngưỡng ⇒ Play có thể giảm khả năng hiển thị ứng dụng và hiện cảnh báo trên trang cửa hàng. Mục tiêu nội bộ của HỏiCon
(crash-free ≥ 99%, tức sự cố ≤ 1%) chặt hơn ngưỡng tổng thể 1,09% một chút, nên đạt mục tiêu là đồng thời tránh ngưỡng xấu.

## Điều kiện để số đo có ý nghĩa
- Android vitals chỉ hiện khi có **đủ dữ liệu** (đủ người dùng hoạt động); ở thí điểm vài chục máy có thể không hiện hoặc nhảy
  mạnh theo một người. Khi dùng số, **ghi cỡ mẫu** (số người dùng hoạt động) và nói rõ nếu dưới ngưỡng tin cậy.
- Chỉ tính bản phát hành thật (Play internal/closed testing), không tính máy ảo hay bản debug tự cài.
- Một lỗi trên ít kiểu máy nhưng nhiều người (ví dụ một hãng) có thể ẩn trong số tổng: xem bảng theo kiểu máy/hãng, khớp với
  bảng hãng máy đã dùng để đo heartbeat (spec 032 SC-007).

## Ghi vào báo cáo thí điểm
Báo cáo thí điểm (`docs/PILOT-PROTOCOL.md`, lệnh `python -m hoicon.ops.pilot …`) có dòng "crash-free (Play vitals, ghi cỡ mẫu)".
Điền bằng tay từ Play Console, theo mẫu:

> Crash-free 28 ngày: **XX,X%** (tỷ lệ sự cố người dùng cảm nhận được Y,Y%; ANR Z,Z%) · phiên bản `0.x.y (n)` · **cỡ mẫu: N
> người dùng hoạt động** · nguồn: Android vitals, đọc ngày DD/MM/YYYY · máy ảo/debug không tính.

Nếu Play chưa hiện số (thiếu dữ liệu) ghi: "Android vitals chưa đủ dữ liệu (N người dùng); chưa kết luận". Không dùng Firebase
hay con số từ máy ảo thay thế.

## Khi nào quay lại Crashlytics
Chỉ khi Minh duyệt (MASTER-PLAN §8 mục 13) **và** có project Firebase + `google-services.json` ngoài git: thêm SDK, mục đích
đồng ý mới (enum + phiên bản văn bản, `consent-copy`), cập nhật `PRIVACY-DPIA.md` và khai báo data safety trên Play.
