# ADR-011: Danh sách đe dọa trên máy dạng bucket k-ẩn danh, không phát tập h1

- Trạng thái: **Chấp nhận** (18/10/2026, Tiến duyệt và ủy quyền cho Claude ghi vào ADR; Minh chốt phạm vi khi duyệt PR).
  Đề xuất 16/10/2026, soạn bởi Claude cho Tiến; spec 026, nhiệm vụ T001.
- Liên quan: ADR-001 (luật tất định trên máy), ADR-006 (HMAC số điện thoại), ADR-009 (lõi tác tử);
  `specs/026-verification-threat` (spec, plan D1); `docs/DATA-MODEL.md` §2 (`threat_indicators`); CLAUDE.md luật 1–2.
- **Phần ADR-006 bị sửa đổi: đúng một ý** ("Danh sách đe dọa gửi xuống máy dạng tập h1"). Thân ADR-006 không bị sửa.
  Dòng "Sửa đổi bởi ADR-011" đã gắn vào ADR-006 khi chấp nhận (18/10/2026).

## Bối cảnh
Muốn tra ngoại tuyến (US-06.3), máy phải trả lời được "h1 này có trong danh sách không" mà không cần mạng, vì
`onScreenCall` chạy trên main thread với hạn 5 giây của Telecom. ADR-006 ghi danh sách gửi xuống máy dạng tập h1 và
thừa nhận h1 dò ngược được.

Vấn đề: `h1 = SHA-256("hoicon:v1:" + E164)` không có muối. Không gian số di động Việt Nam ước tính S ≈ 3,6 × 10⁸
(khoảng 36 đầu số 3 chữ số × 10⁷). Ai cài app đều chạy được toàn bộ không gian đó trong vài giây trên một máy tính.
Tập h1 trên máy nghĩa là **cả danh sách lộ nguyên vẹn**, kể cả số của người vô tội bị kẻ gian giả mạo. Bloom filter chính
xác cao không khá hơn. Khóa nhúng trong app cũng vô ích, vì app công khai trên Play.

Ngoài ra máy chủ hiện không có h1 (chỉ `HMAC(pepper[kid], h1)` + `last3`), nên không thể phát tập h1 nếu không lưu thêm gì.

## Các phương án

| Phương án | Ngoại tuyến | Lộ danh sách | Máy chủ phải lưu | Kết luận |
|---|---|---|---|---|
| A. Tập h1 (ADR-006 cũ) | chính xác | **toàn bộ**, dò ngược trong vài giây | h1 hoặc `value_enc` | loại |
| B. Chỉ tra trực tuyến | không | không | không | loại: mất US-06.3 khi mất mạng, thêm độ trễ mạng vào `onScreenCall` |
| **C. Bucket k-ẩn danh** | "có thể" (khớp nhầm có giới hạn) | mỗi chỉ báo lẫn trong ≈ S/2^b số | `bucket_enc` mã hóa | **chọn** |

## Quyết định (phương án C)
- **Bucket.** `bucket24 = int(h1[0:6], 16)`. h1 đã là SHA-256 nên 24 bit đầu phân bố đều, máy không cần băm thêm. Ảnh chụp
  phát `bucket = bucket24 >> (24 − b)` với `b = HOICON_THREAT_BUCKET_BITS` (mặc định **22**, giới hạn 16–24).
- **k-ẩn danh.** Số di động mỗi bucket ≈ S / 2^b:
  - b = 22 ⇒ 3,6 × 10⁸ / 4.194.304 ≈ **86 số**;
  - b = 24 ⇒ ≈ 21 số;
  - b = 16 ⇒ ≈ 5.500 số.

  Kẻ tấn công chỉ biết "một trong khoảng 86 số này *có thể* có tên trong danh sách". Đây là **ước tính từ công thức**
  (S là ước lượng, không phải số liệu đo), không phải đảm bảo mật mã.
- **Tỉ lệ khớp nhầm** cho một số lạ ngẫu nhiên là `N / 2^b` (N = số bucket phân biệt). Với b = 22: N = 2.000 ⇒ 0,05%;
  N = 10.000 ⇒ 0,24%. Chính sách chọn `bucket_bits`: khi tỉ lệ này vượt **0,25%** thì ops nâng b lên 23–24 (đổi lấy
  khoảng 21–43 số mỗi bucket). Ngưỡng 0,25% là giới hạn đề xuất.
- **Hệ quả của khớp nhầm.** R1 vốn đã `high` cho mọi chuỗi "số lạ → app tài chính". Khớp bucket chỉ nâng lên `critical`,
  và AlertService cảnh báo ở cả hai mức. Máy chủ vẫn tra chính xác h1 khi nhận sự kiện (`prepare_event`), và lý do "có trong
  danh sách cảnh báo" gửi người giám hộ chỉ lấy từ kết quả tra chính xác đó. Khớp nhầm không bao giờ tạo khẳng định sai
  gửi tới con.
- **Lưu ở máy chủ: `bucket_enc`, không lưu bucket dạng rõ.** Bucket24 rõ cạnh `last3` cho phép kẻ lấy bản sao DB thử S số
  với SHA-256 để ra số điện thoại (24 bit + 3 số cuối gần như xác định duy nhất một số), tức vô hiệu pepper của ADR-006.
  Vì vậy cột `threat_indicators.bucket_enc = "<kid>." + base64url(nonce ‖ AES-256-GCM(bucket24, HOICON_DATA_KEY_<kid>, aad))`,
  `aad = "hoicon:threat:bucket:v1:<kid>:<value_hmac>"`. Tráo bản mã giữa hai dòng làm giải mã hỏng. Thực hiện theo mẫu
  `encrypt_chat_id` (ADR-010 D1). Chỉ giải mã khi dựng ảnh chụp, không lưu lại, không log.
- **Không có delta.** Ảnh chụp ≈ 3 byte mỗi bucket: 10.000 chỉ báo ≈ 30 KB (≈ 40 KB base64). Không cần delta tới khoảng
  100.000 chỉ báo. `since` là phiên bản ảnh chụp (`sha256(nội dung)[:16]`): trùng thì trả 304.

## Hệ quả
- Tốt: danh sách trên máy không dò ngược được thành danh sách số điện thoại; tra ngoại tuyến vẫn ≤ 5 ms; không đổi đường dừng
  an toàn (luật tất định, không I/O).
- Đánh đổi: có khớp nhầm có giới hạn trên máy (kết quả "có thể", không bao giờ "chắc chắn"); k-ẩn danh chỉ là bảo vệ thống
  kê, kẻ có danh sách ứng viên nhỏ (ví dụ danh bạ của một người) vẫn kiểm tra được từng ứng viên.
- Dòng cũ thiếu `bucket_enc` không xuống máy cho tới khi nạp lại tệp seed (có h1). Mất `HOICON_DATA_KEY_<kid>` thì nạp
  lại seed là dựng lại được.
- Nếu Tiến **không** chấp nhận: phương án lùi là giữ tập h1 (A), nhưng khi đó phải sửa DPIA và có ý kiến Minh (dữ liệu bên
  thứ ba bị lộ). Plan 026 vẫn chạy được với `bucket_bits = 24`.
- Android: xóa bảng `threat_hashes` của Room v1 (lưu h1 không mã hóa, chưa từng được ghi).

## Hạn chế đã biết (rà soát độc lập spec 026)
- **Khóa dùng chung.** `bucket_enc` dùng cùng `HOICON_DATA_KEY_<kid>` với `chat_id` Zalo (AAD tách miền, nhưng không tách
  phạm vi lộ khóa). Lộ khóa này mà không lộ pepper vẫn cho `bucket24` + `last3` ≈ xác định số điện thoại, tức pepper
  ADR-006 vô hiệu với cả danh sách. Cân nhắc khóa riêng hoặc HKDF khi Tiến duyệt ADR.
- **k-ẩn danh chỉ là ước tính** trên số đang dùng. Ảnh chụp bucket cộng với oracle chính xác `POST /v1/lookups` thu hẹp
  việc dò (≈ 86 ứng viên mỗi bucket ở b = 22, tốn ≈ 86 lượt tra; hạn mức gia đình 200/ngày), và `version` đổi cho biết có
  bucket mới. Hướng giảm: nâng `bucket_bits`, hạn mức đời của thiết bị, cảnh báo actor có tỉ lệ `unknown` rất cao.
