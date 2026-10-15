# Spike P1-S3: Kênh Zalo cho người giám hộ

- Spec: `specs/002-zalo-guardian-channel` · Nhánh `feat/002-zalo-guardian-channel` · Quyết định: **ADR-010** (D1/D2 Tiến duyệt 15/10; Minh xác nhận ở PR; số đo thật còn nháp)
- Trạng thái: code xong ở chế độ mock (T001–T023); **T024 BLOCKED: chờ token bot thật** — chưa đo SC-001

## 1. Tra tài liệu chính thức (T001 · research R1)

Ngày tra: **15/10/2026**. Nguồn chính thức: Zalo Bot Platform — tài liệu `https://bot.zapps.me/docs/` (mục lục: Create Bot,
Authorization, Using the API, API Reference, Webhook, Error Codes, Terms of Use) và trang sản phẩm `https://bot.zapps.me/`.
Tra bằng cách đọc trang (không gọi API thật, chưa dùng token). Chỗ tài liệu tự mâu thuẫn hoặc im lặng được ghi rõ.

| Mục R1 | Kết quả tra | Nguồn |
|---|---|---|
| Base URL, token | `https://bot-api.zaloplatforms.com/bot<BOT_TOKEN>/<method>`, bắt buộc HTTPS, **token nằm trên đường dẫn URL**. Phản hồi luôn là JSON: `ok`, `result`, `description`, `error_code` | `/docs/call-api/` |
| Phương thức | `getMe`, `getUpdates`, `setWebhook`, `testWebhook`, `deleteWebhook`, `getWebhookInfo`, `sendMessage`, `sendPhoto`, `sendSticker`, `sendVoice`, `sendChatAction` — đều `POST`, `application/json` | `/docs/` (mục lục) |
| Cập nhật webhook | Thân: `{"ok": true, "result": {"event_name": …, "message": {…}}}`. `event_name` ∈ `message.text.received`, `message.image.received`, `message.sticker.received`, `message.voice.received`, `message.unsupported.received`. `message` có `from{id, display_name, is_bot}`, `chat{id, chat_type: PRIVATE｜GROUP(Beta)}`, `text`; ví dụ mẫu còn có `message_id`, `date` (mili-giây) dù bảng đặc tả không liệt kê. Tài liệu chỉ có ví dụ đầy đủ cho `message.text.received`; bảng ghi kiểu `message` là String nhưng ví dụ là object ⇒ **tài liệu chưa nhất quán, tin ví dụ** | `/docs/webhook/` |
| **Mã cập nhật (khóa chống trùng)** | **Không có `update_id`** trong thân webhook (cũng không thấy ở `getUpdates`). Dùng **`result.message.message_id`** ⇒ khóa job `zalo:{bot_id}:{message_id}` (plan/tasks ghi `update_id` — cần sửa) | `/docs/webhook/`, `/docs/apis/getUpdates/` |
| Xác thực webhook | Header `X-Bot-Api-Secret-Token` = `secret_token` đã đặt; ví dụ mẫu trả **403** khi sai. Spec 002 chọn **401** — Zalo không nói có phản ứng khác nhau giữa 401/403 | `/docs/webhook/` |
| Yêu cầu phản hồi, gửi lại | Không nêu mã 200 bắt buộc, **không mô tả cơ chế gửi lại** (⇒ vẫn giữ chống trùng; chưa chứng minh được "Zalo gửi lại khi 503"). `testWebhook` coi 2xx là `webhook.ok`, `err.timeout` ⇒ "trả 2xx ngay, xử lý bất đồng bộ" | `/docs/apis/testWebhook/` |
| `setWebhook` | Tham số `url` (HTTPS, truy cập được từ Internet công khai; localhost/IP nội bộ/miền nội bộ Zalo bị từ chối; **không theo redirect**) và `secret_token` (8–256 ký tự). Sau khi lưu, Zalo **tự gửi thử một request** tới URL và trả `verification{ok, url, outcome, hint}`; URL vẫn được lưu kể cả khi thử thất bại. Thân/ header của request thử **không có tài liệu** ⇒ webhook phải trả 2xx cho thân không có `message` | `/docs/apis/setWebhook/` |
| `getWebhookInfo`, `deleteWebhook` | Không tham số. Trả `result{url, updated_at}` (sau xóa `url` rỗng) | `/docs/apis/getWebhookInfo/`, `/docs/apis/deleteWebhook/` |
| `getUpdates` vs webhook | "Độc lập và loại trừ lẫn nhau": đang có webhook thì `getUpdates` không chạy (phải `deleteWebhook`). Chỉ khuyên dùng cho dev; một cập nhật mỗi lần gọi (theo SDK bên thứ ba, **chưa có trong tài liệu chính thức**) | `/docs/apis/getUpdates/` |
| Gửi tin | `sendMessage`: `chat_id` (String, bắt buộc), `text` (String **1–2000 ký tự**, bắt buộc), tùy chọn `parse_mode` (`markdown`｜`html`), `text_styles[{start,len,st}]`. Thành công: `result{message_id, date}` | `/docs/apis/sendMessage/` |
| **Nút bấm / bàn phím** | **Không có tài liệu**: `sendMessage` không có `reply_markup`/keyboard; webhook không có sự kiện callback ⇒ **chỉ dùng phản hồi văn bản 1/2/3** (ADR-003 đã cho phép). T016 bỏ nhánh nút bấm | `/docs/apis/sendMessage/`, `/docs/webhook/` |
| Mã lỗi | HTTP `400` sai đường dẫn/tên API · `401` token hết hạn/không hợp lệ · `403` "Internal server error" (nhãn tài liệu) · `404` yêu cầu truy cập không hợp lệ · `408` quá thời gian · `429` vượt hạn mức. Có trường `description`. `testWebhook` ghi thêm: vượt giới hạn gọi API/ngày ⇒ `ok:false`, **`errorCode: 426`** (viết camelCase, khác `error_code` ở nơi khác). **Không có mã riêng cho "chat không tồn tại/bị chặn"** | `/docs/error-code/`, `/docs/apis/testWebhook/` |
| Hạn mức gói Basic | Miễn phí; tối đa **3 bot**; mỗi bot tương tác tối đa **50 người dùng**; tối đa **3.000 tin nhắn/tháng**; 3 nhóm chat (Beta). Gói Pro 129.000đ/tháng "sắp ra mắt", không có số liệu. **Không nêu** 3.000 là đếm tin gửi đi hay cả tin đến ⇒ tạm đếm tin gửi đi, đo lại ở T024 (xem ADR-010 §Hạn mức) | `https://bot.zapps.me/` |
| Giới hạn tốc độ | **Không có tài liệu** (ngoài trần ngày `426` ở trên) | `/docs/call-api/` |
| Điều khoản | Không có con số hạn mức; không cấm hay cho phép rõ "gửi tin chủ động/tự động" và **không có khái niệm cửa sổ 24 giờ**. Điều VIII.2 cấm nội dung lừa đảo/mạo danh tổ chức và dùng đầu ra cho quyết định tài chính/pháp lý **không có người có chuyên môn giám sát** — cần chú ý khi viết lời nhắn "đây là lừa đảo"; tin của ta chỉ gợi ý, mọi quyết định do con cháu. Từ 18 tuổi (13–17 cần người giám hộ). Zalo có quyền tạm ngưng không báo trước ⇒ cần kênh dự phòng | `/docs/terms/` |

### Hệ quả cho thiết kế (chép vào ADR-010 khi viết T004)

1. **Khóa chống trùng** là `message_id`, không phải `update_id` ⇒ sửa `plan.md`, `tasks.md` T011, `contracts/README.md`, `docs/API.md` khi tới task đó.
2. **Không có nút bấm** ⇒ người giám hộ trả lời văn bản; mẫu tin phải ghi rõ "trả lời 1 / 2 / 3".
3. **Không biết Zalo có gửi lại webhook hay không** ⇒ giữ chống trùng bằng `jobs.idempotency_key` và trả 503 khi DB lỗi, nhưng
   không được hứa "không mất cập nhật" trong báo cáo cho đến khi đo trên bot thật (T024).
4. **`testWebhook` gửi thân chưa rõ** ⇒ hợp đồng `zalo_update.v1` chỉ **bắt buộc** `ok` + `event_name`; `message` bắt buộc
   khi là tin chữ. Handler không được lỗi với sự kiện không phải tin chữ.
5. **Lỗi gửi**: phân loại theo HTTP status (`401/400/404` ⇒ vĩnh viễn; `408/429/5xx/mạng` ⇒ thử lại); không phân biệt được "chat bị chặn" ⇒
   mọi lỗi 4xx khác 408/429 coi là vĩnh viễn ⇒ `fallback_required`.
6. **`display_name`** có trong thân webhook nhưng là tên thật ⇒ **không lưu, không log** (luật 1); hợp đồng chỉ khai báo để biết, mã không đọc.
7. `chat.id` trùng `from.id` ở chat PRIVATE trong ví dụ mẫu; mã lưu theo `chat.id` (để gửi) và HMAC theo `from.id` (để tra cứu) — ADR-010 D1.

## 2. Đã dựng (chế độ mock; chưa gọi Zalo thật)

| Thành phần | Tệp |
|---|---|
| Hợp đồng cập nhật webhook | `docs/schemas/zalo_update.v1.json` + `fixtures/zalo_update.v1.{valid,invalid}.json` (định danh hư cấu) |
| Zalo client (Live/Mock, lọc log token, lệnh vận hành webhook) | `backend/src/hoicon/channels/zalo.py` |
| Mã hóa `chat_id` (AES-256-GCM, kid), HMAC tra cứu, băm mã ghép | `backend/src/hoicon/domain/pii.py` |
| Bảng `families`, `members`, `pairing_codes`, `messages_out` | migration `0003` + `db/models.py` (ADR-010 D2) |
| Webhook `POST /webhooks/zalo/{bot_id}` (+ ứng dụng con cho đường hầm) | `api/webhooks.py` |
| Cổng gửi tin (một lần, câu công khai AI, hạn mức, dự phòng) | `channels/guardian.py` |
| Ghép `/start <mã>`, phản hồi 1/2/3 | `channels/updates.py`, `channels/inbound.py` |
| Lệnh vận hành | `ops/zalo_webhook.py` (set/info/delete) · `ops/pairing_code.py` · `ops/zalo_simulate.py` |
| `family_id` vào đồ thị sự cố | `agents/runtime.py`, `agents/incident_graph.py` |

## 3. Số đo SC-001 (T024)

**BLOCKED: chờ token bot thật (W0-3, Tiến/Minh).** Chưa đo được: p95 ≤ 5 000 ms từ lúc xếp tin tới lúc Zalo xác nhận với bot dev
thật (n ≥ 20) và ≥ 5 lần bấm giờ tới khi tin hiện trên điện thoại. **Không tick SC-001.**

Số đo **MOCK** (chỉ để biết phần xử lý của máy chủ, KHÔNG phải bằng chứng SC-001):

| Phép đo | n | p50 | p95 | max | Điều kiện |
|---|---|---|---|---|---|
| `jobs.created_at` → `messages_out.sent_at`, `MockZaloClient` | 20 | 6,6 ms | 8,3 ms | 11,1 ms | 15/10/2026, máy dev Linux, Postgres 17 trong Docker; gọi thẳng `send_to_guardian` ngay sau khi xếp job — **không** gồm chu kỳ lấy job của worker (tối đa 0,5 s), mạng, hay Zalo |

Khi có token (quickstart "Thật"): lặp `python -m hoicon.agents.spike demo` ≥ 20 lần, lấy `sent_at − jobs.created_at` từ `messages_out`,
bấm giờ tay ≥ 5 lần, ghi bảng n/p50/p95/ngày/bot vào mục này, rồi hoàn thiện ADR-010 (T025).
