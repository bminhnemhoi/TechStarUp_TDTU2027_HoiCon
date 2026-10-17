# ADR-010: Lưu định danh Zalo bằng mã hóa + HMAC, migration 0003 tạo 4 bảng, kênh dự phòng và rủi ro gửi lặp

- Trạng thái: **D1 và D2 được Tiến (kỹ sư chủ trì nhánh) duyệt ngày 15/10/2026**; Minh xác nhận lại khi duyệt PR. Phần "Kết quả
  đo" và hạn mức thật vẫn **NHÁP** tới khi có token (T024/T025). Soạn bởi Claude cho Tiến; spec 002, nhiệm vụ T004.
- Liên quan: ADR-003 (Zalo Bot Platform), ADR-006 (HMAC), ADR-009 (job, `notify_guardian`); `specs/002-zalo-guardian-channel`
  (spec, research R1–R5, data-model); `docs/spikes/P1-S3-zalo.md` §1 (tài liệu Zalo tra ngày 15/10/2026); CLAUDE.md luật 1–2, 6, 9, 11
- Đã duyệt D1/D2 ⇒ migration 0003 (T006) và các task cần bảng mới được viết ở nhánh này. Minh vẫn là người chốt phạm vi:
  nếu Minh bác khi duyệt PR thì quay lại phương án lùi của D2 bằng migration mới (0003 chưa lên `main` nên còn sửa được).
- Phần "Kết quả đo" và quyết định cuối về hạn mức được hoàn thiện ở T025, sau T024 (cần token bot dev — W0-3, Minh).

## Bối cảnh
Gửi tin Zalo cần `chat_id` thật của người giám hộ. DATA-MODEL ghi `members.zalo_user_ref (HMAC)` — không đảo ngược nên
không gửi được; luật 1 cấm lưu Zalo ID thô. Luồng `/start <mã>` cần `families`, `members`, `pairing_codes`; tin đi cần
`messages_out` để đếm hạn mức và chống gửi lặp. Tra cứu tài liệu chính thức (15/10/2026) còn cho thấy: webhook **không có
`update_id`**, **không có nút bấm/callback**, không có tài liệu về giới hạn tốc độ hay việc Zalo gửi lại webhook.

## D1 — Quyết định: `chat_id` mã hóa AES-256-GCM + HMAC tra cứu
- Cột `members.zalo_chat_enc` = `"<kid>.<base64url(nonce‖ciphertext‖tag)>"`, AES-256-GCM, nonce 12 byte ngẫu nhiên mỗi lần,
  khóa `HOICON_DATA_KEY_<kid>` (32 byte, hex 64 ký tự, **ngoài DB**, `init_env` sinh, `check_keys` kiểm). `kid` nằm
  trong dữ liệu xác thực (AAD) nên đổi tiền tố `kid` làm giải mã hỏng. Chỉ giải mã **lúc gửi**, không lưu lại, không log.
- Cột `members.zalo_user_hmac` = `HMAC-SHA256(pepper[kid], "hoicon:zalo:v1:" + bot_id + ":" + user_id)` (+ `zalo_hmac_kid`)
  để tra "người nhắn tới là ai" và chống trùng; tiền tố miền riêng nên không lẫn với HMAC của `h1` số điện thoại (ADR-006)
  dù cùng pepper. `bot_id` không chứa `:`. Ràng buộc `unique (zalo_bot_id, zalo_user_hmac)`.
- Hiện thực đã có và đã test: `hoicon.domain.pii` (`hmac_zalo`, `encrypt_chat_id`, `decrypt_chat_id`); lỗi giải mã chỉ ném
  `ValueError` không mang dữ liệu.
- Không lưu `display_name` (tên thật) từ webhook; không lưu văn bản người giám hộ trả lời (chỉ ánh xạ 1/2/3 ⇒ quyết định).
- Rút đồng ý / xóa gia đình ⇒ xóa `zalo_chat_enc` (job retention ở spec 034).

### Phương án đã loại cho D1
| Phương án | Vì sao loại |
|---|---|
| Lưu `chat_id` thô | Vi phạm luật 1; DB lộ là lộ định danh Zalo của người giám hộ |
| Chỉ lưu HMAC | Không gửi được tin (HMAC không đảo ngược) |
| Mã hóa bằng `pgcrypto` trong Postgres | Khóa đi qua câu SQL ⇒ dễ lọt vào log truy vấn/`pg_stat_statements` |
| Bộ lưu bí mật bên ngoài (KMS/Vault) | Quá nặng cho quy mô thí điểm ≤ 150 người giám hộ; có thể thay sau vì `kid` đã cho phép xoay khóa |

## D2 — Quyết định: migration 0003 tạo đúng 4 bảng
`families`, `members`, `pairing_codes`, `messages_out` theo DATA-MODEL §2, cột Zalo theo D1 (chi tiết:
`specs/002-zalo-guardian-channel/data-model.md`):
- `members`: thêm `zalo_user_hmac`, `zalo_hmac_kid`, `zalo_chat_enc`, `zalo_bot_id` (thay `zalo_user_ref`); unique
  `(family_id, guardian_rank)` khi `role = guardian`; unique `(zalo_bot_id, zalo_user_hmac)`.
- `pairing_codes`: chỉ lưu `code_hash`, hết hạn 15 phút, một lần dùng.
- `messages_out`: thêm `member_id` (biết người nhận để ánh xạ phản hồi 1/2/3 về đúng sự cố) và `job_key` unique
  (gửi đúng một lần); `status` ∈ `queued | sent | held_quota | failed | fallback_required`; index `(bot_id, quota_month, status)`.
- Spec 020 thêm phần còn lại (`devices`, `consents`, `trusted_contacts`, `action_tokens`) ở migration sau 0003.
- Hệ quả tài liệu: sửa DATA-MODEL §2 (cột Zalo + 2 cột mới của `messages_out`) ở T021. Migration đã lên `main` là bất biến (luật 11).

### Phương án đã loại cho D2
| Phương án | Vì sao loại |
|---|---|
| Bảng tạm cho spike | Rác nằm vĩnh viễn trong migration bất biến |
| Hoãn `/start` sang spec 020 | Spike không đo được đầu–cuối; **giữ làm phương án lùi nếu Minh từ chối D2** (khi đó chỉ đo chiều gửi bằng mock và bot dev, và ghi rõ) |

## Điều chỉnh ADR-003 theo tài liệu thật
- Chống trùng webhook dùng **`result.message.message_id`** (Zalo không gửi `update_id`): khóa job `zalo:{bot_id}:{message_id}`,
  tái dùng `jobs.idempotency_key`, không thêm bảng.
- **Không có nút bấm**: người giám hộ trả lời văn bản **1 / 2 / 3**; mẫu tin ghi rõ cách trả lời. (ADR-003 đã cho phép.)
- Webhook trả **2xx ngay** (Zalo coi 2xx là `webhook.ok`, quá hạn là `err.timeout`); sự kiện không phải tin chữ vẫn trả 200.
  Zalo tự gửi một request thử khi `setWebhook` mà thân không có tài liệu ⇒ handler phải chịu được thân thiếu `message`.
- Sai secret trả 401 (ví dụ của Zalo dùng 403; Zalo không nói có phản ứng khác nhau giữa hai mã).

## Hạn mức và điều khoản (sẽ chốt số ở T025)
- Gói Basic miễn phí: **3 bot × 50 người dùng × 3.000 tin/tháng** (trang `bot.zapps.me`); gói Pro "sắp ra mắt". Tài liệu **không nói**
  3.000 tính tin gửi đi hay cả tin đến, và **không có** giới hạn tốc độ (chỉ có trần gọi API theo ngày, lỗi `426`).
- Tạm thời: bộ đếm `messages_out` đếm **tin gửi đi**, ngưỡng cảnh báo 80% / dừng tin không khẩn 95% cấu hình được; tin sự cố
  luôn gửi. Nếu T024 cho thấy tin đến cũng tính, hạ trần cấu hình — **không cần đổi lược đồ**. Hết hạn mức ⇒ `fallback_required`.
- Điều khoản (Zalo Bot Platform): không cấm gửi tin tự động, không có cửa sổ 24 giờ; nhưng điều VIII.2 cấm dùng đầu ra
  cho quyết định tài chính/pháp lý **không có người có chuyên môn giám sát** và Zalo có quyền **tạm ngưng không báo trước**.
  ⇒ Lời nhắn chỉ *gợi ý*, quyết định do con cháu; luôn có kênh dự phòng.

## Kênh dự phòng
- Mặc định: trang hành động web `/a/[token]` (spec 023) với cùng các hành động; khi gửi Zalo thất bại vĩnh viễn hoặc hết hạn
  mức, `messages_out.status = fallback_required` để spec 023 xử lý.
- Telegram **chỉ** khi Zalo thất bại về điều khoản hoặc kỹ thuật (theo ADR-003); quyết định lúc đó là ADR mới.

## Rủi ro gửi lặp
- Gửi "đúng một lần" bằng khóa job `incident:msg:template` + dòng `messages_out.job_key` unique; trước khi gọi Zalo kiểm
  dòng đã `sent` ⇒ bỏ qua, nên retry sau khi đã ghi `sent` không gửi lại.
- **Còn lại:** Zalo đã nhận nhưng ta timeout/mất mạng trước khi ghi `sent` ⇒ lần thử lại gửi **lần hai**. Tài liệu Zalo không
  có khóa chống trùng khi gửi. **Chấp nhận gửi lặp hiếm** cho tin sự cố (gửi thừa an toàn hơn bỏ sót); chỉ thử lại khi lỗi là
  `retryable` (mạng, 408, 429, 5xx), còn 4xx khác coi là vĩnh viễn ⇒ `fallback_required`. Đo tần suất ở T024.

## Hệ quả
- (+) DB lộ không làm lộ Zalo ID/`chat_id` (cần thêm khóa dữ liệu và pepper); vẫn gửi được tin; tra cứu và chống trùng bằng HMAC.
- (+) Xoay khóa được nhờ `kid`; migration một lần cho đủ bốn bảng spike cần, không bảng rác.
- (−) **Mất `HOICON_DATA_KEY_<kid>` ⇒ mọi người giám hộ đã ghép phải ghép lại** (HMAC vẫn còn nhưng không gửi được); phải
  sao lưu khóa cùng chỗ với pepper. Khóa nằm cùng máy với tiến trình API ở giai đoạn dev; chuyển sang bí mật của VPS ở spec 012.
- (−) Phụ thuộc nền tảng bên thứ ba có tài liệu chưa nhất quán (kiểu `message`, `error_code`/`errorCode`), không có cơ chế
  gửi lại webhook được mô tả ⇒ chưa được tuyên bố "không mất cập nhật" trước khi đo bot thật.
- (−) Chỉ trả lời 1/2/3 bằng chữ: người giám hộ có thể gõ sai ⇒ mẫu hướng dẫn lại thay vì hành động.

## Điều chỉnh khi hiện thực (15/10/2026, sau review bảo mật và UX)
Các điểm dưới đây lệch hoặc làm rõ D1/D2; không đổi quyết định, chỉ đổi chi tiết:
- **`messages_out.family_id` rỗng được, FK `ON DELETE SET NULL`**: tin trả lời người chưa ghép vẫn phải tính vào hạn mức; xóa gia
  đình không được làm tụt bộ đếm. `incident_id` chưa có FK (bảng `incidents` ở spec 021).
- **Job `zalo_update` không mang chữ thô hay Zalo ID thô**: webhook băm/mã hóa định danh và phân loại văn bản ngay; sau khi xử
  lý xong, `chat_enc` và `code_hash` bị xóa khỏi payload. Thêm chỉ mục `ix_jobs_kind_created` (trong 0003) cho truy vấn đếm tần suất.
- **Bản mã `chat_id` gắn với chủ sở hữu**: AAD gồm `kid` và `zalo_user_hmac` ⇒ chép bản mã từ người này sang hàng người khác thì
  giải mã hỏng (không chuyển hướng được cảnh báo bằng quyền ghi DB).
- **Ghép đôi**: hạng người giám hộ gán tự động (hạng trống nhỏ nhất, tối đa 2); mã gắn với gia đình, không gắn hạng. Chống dò mã
  6 số: 10 lần/15 phút mỗi Zalo, 100 lần/15 phút mỗi bot, im lặng khi vượt; mỗi gia đình dev chỉ một mã còn hiệu lực. Mã không
  dùng được vì bất cứ lý do gì (sai, hết hạn, đã dùng, gia đình đủ người, Zalo đã ở gia đình khác) đều nhận **cùng một câu**.
- **Chế độ gửi**: `mock` bị từ chối khi `HOICON_ENV=prod`; tin gửi bằng mock ghi `messages_out.error='mock'`; chạy mock có cảnh báo log.
- **Luật 8 đối xứng**: sự cố demo chỉ tới gia đình demo và ngược lại; sự cố diễn tập thiếu nhãn `[DIỄN TẬP]` bị cổng gửi từ chối.
- **Zalo không có nút bấm** ⇒ phản hồi bằng chữ 1/2/3; lựa chọn 1 ("đã gọi được, an toàn") chỉ dành cho người đã gọi được,
  mẫu tin luôn nhắc "chưa gọi được thì gọi lại rồi trả lời sau".

## Rủi ro còn lại (chấp nhận có điều kiện, chuyển cho spec sau)
| Rủi ro | Mức | Cách xử lý / spec |
|---|---|---|
| Kẻ dùng nhiều tài khoản Zalo vẫn có xác suất nhỏ đoán trúng mã 6 số đang hiệu lực rồi chiếm một hạng người giám hộ | Trung bình | Bước xác nhận thứ hai trên app và thu hồi hạng: spec 020. Giảm thiểu hiện có: giới hạn lần thử theo Zalo/bot, một mã còn hạn mỗi gia đình, mã hết hạn 15 phút, bot Basic chỉ ≤ 50 người dùng |
| Chưa có `consents` cho `guardian_channel` và chưa có job xóa theo hạn lưu | Trung bình | Spec 011/020/034. Cho tới lúc đó bot dev **chỉ dùng với tài khoản Zalo của đội**; không bật cho gia đình thí điểm |
| `HOICON_ENV` mặc định `dev` nếu quên đặt (ảnh hưởng `/mcp/threat`, `zalo_simulate`) | Trung bình | Đặt `HOICON_ENV=prod` ở VPS (spec 012); mock bị từ chối ở prod |
| Hai sự cố đồng thời cho cùng một người giám hộ: "1/2/3" áp vào sự cố có tin gần nhất | Thấp | Gắn mã ngắn vào tin khi có nhiều sự cố (spec 023) |
| Xoay khóa `kid` chưa dùng được (`Settings` chỉ có `data_key_1`; tra cứu bỏ qua `zalo_hmac_kid`) | Thấp | Thêm trường theo kid và tra theo `(kid, hmac)` khi thật sự xoay |
| Kẻ nhắn bot hàng loạt vẫn tiêu hao hạn mức (đã chặn trả lời sau 10 tin/giờ, nhưng tin đến có thể tính vào 3.000) | Thấp–TB | Đo ở T024 xem tin đến có tính không; nếu có, hạ trần cấu hình |
| `messages_out` chưa có cờ `is_drill`/`is_demo` (luật 8 "cờ ở mọi nơi") | Thấp | Thêm khi có bảng `incidents` (spec 021) |
| Dòng "Mức nguy cơ: …" trong tin chi tiết (câu chữ P1-S4) | Thấp | `ux-elder-reviewer` P2-07/P2-08 |

## Cần Tiến/Minh xác nhận
1. **D1, D2 — Tiến đã duyệt 15/10/2026**; Minh xác nhận lại khi duyệt PR (0003 chưa lên `main`, còn sửa được).
2. Chấp nhận **gửi lặp hiếm** cho tin sự cố? (Đề xuất: có.)
3. Chấp nhận bảng **rủi ro còn lại** ở trên cho giai đoạn bot dev chỉ dùng với tài khoản của đội?
4. Cấp token bot dev (W0-3) để làm T024 và hoàn thiện ADR này (T025: kết quả đo SC-001, hạn mức thật, tin đến có tính vào 3.000 không).
