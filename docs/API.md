# API HỏiCon `/v1`

> Trạng thái: **khung** (P0-05). Nguồn sự thật cuối cùng là OpenAPI do FastAPI sinh (`/openapi.json`) + JSON Schema
> trong `docs/schemas/`. Đổi API ⇒ cập nhật file này + `bash scripts/gen-api-client.sh` (client TS cho web).

## Xác thực
- Thiết bị (spec 020): `Authorization: Bearer <access_token>`; JWT HS256 ký bằng `HOICON_DEVICE_JWT_SECRET` (≥ 32 ký tự), sống **30 ngày**,
  claim `sub` (device_id), `family_id`, `member_id`, `role=protected`, `iss=hoicon`, `aud=hoicon-device`. Mỗi lần gọi còn đối chiếu DB
  (thiết bị tồn tại, chưa `revoked_at`) ⇒ thu hồi có hiệu lực ngay. Refresh token (32 byte ngẫu nhiên, DB chỉ giữ SHA-256) cấp cùng
  lúc; endpoint làm mới chưa có. Người giám hộ: magic link / action token một lần (`/a/[token]`, spec 023) hoặc phiên web (spec 027, mục dưới).
- Người giám hộ trên web (spec 027): `Authorization: Bearer <JWT người giám hộ>` **hoặc** cookie `hc_guardian` (Bearer được ưu tiên; Bearer sai không rơi về cookie). Cookie là JWT `aud=hoicon-guardian` sống **7 ngày**, `HttpOnly; SameSite=Strict; Path=/v1`, thêm `Secure` ở mọi môi trường ngoài `dev/test/ci`. Mỗi request mới đối chiếu DB (thành viên tồn tại, `role=guardian`, cùng gia đình) ⇒ xóa thành viên là các request tiếp theo bị 401 ngay. Giới hạn đã biết: "Đăng xuất" chỉ xóa cookie ở trình duyệt (JWT không có danh sách đen/`jti`) và luồng SSE đã mở chỉ được xác thực lúc mở.
- **CSRF** (lệnh ghi bằng cookie): `POST/PUT/PATCH/DELETE` xác thực bằng cookie phải có `Origin` thuộc danh sách cho phép (`HOICON_WEB_ORIGINS`, cộng nguồn của `HOICON_WEB_BASE_URL`, cộng `http://localhost:3100` ở dev/test/ci) **hoặc** `Sec-Fetch-Site: same-origin`; nếu không ⇒ 403. Lệnh đọc và lệnh dùng Bearer không cần.
- Webhook Zalo: secret trong header `X-Bot-Api-Secret-Token` (so sánh hằng thời gian); chống trùng theo `message_id`
  (Zalo không có `update_id`).

## Thiết bị (app Lính gác)
| Method | Path | Ghi chú |
|---|---|---|
| POST | `/v1/pair` | **đã có** — đổi mã ghép đôi lấy token thiết bị (xem dưới) |
| POST | `/v1/auth/refresh` | |
| POST | `/v1/consents` | **đã có** — ghi thêm dòng đồng ý (xem dưới) |
| GET | `/v1/devices/me` | **đã có** — thông tin thiết bị + trạng thái đồng ý hiện tại (xem dưới) |
| GET | `/v1/config` | cấu hình, phiên bản luật, danh sách app ngân hàng |
| GET | `/v1/threat-list?since=` | tập `h1` bị gắn cờ (delta) |
| POST | `/v1/events` | **đã có** — lô 1–50 sự kiện, idempotent theo id UUIDv7 từ máy (xem dưới) |
| GET | `/v1/incidents/{id}` | **đã có** — chi tiết sự cố + lịch sử chuyển trạng thái (xem dưới) |
| GET | `/v1/families/{id}/incidents` | **đã có** — danh sách sự cố của gia đình (xem dưới) |
| POST | `/v1/incidents/{id}/answers` | **đã có** — trả lời câu hỏi nhanh E8 (xem dưới) |
| GET | `/v1/incidents/{id}/pending-question` | **đã có** — câu hỏi E8 đang chờ xử lý (xem dưới) |
| POST | `/v1/incidents/{id}/ask-child` | nút "Hỏi con" |
| GET | `/v1/incidents/{id}/elder-view` | nội dung E9/E10 cho người cao tuổi |
| POST | `/v1/lookups` | tra cứu số/link/QR (đã băm/che) |
| POST | `/v1/drills/{id}/result` | |
| POST | `/v1/heartbeat` | trạng thái quyền, phiên bản |

### Ghép đôi, đồng ý, thiết bị (spec 020 — đã có)
Hợp đồng: `pair_request.v1.json` / `pair_response.v1.json`, `consent_record.v1.json`, `device_me.v1.json` (fixture `fixtures/*.v1.*.json`).

**`POST /v1/pair`** — không cần token. Thân: `code` (6 số), `app_version`/`rules_version` (`[0-9A-Za-z._+-]`, ≤ 32), `platform`, `device_label?` (máy chủ che số/email trước khi lưu).

| Mã | Khi nào |
|---|---|
| 200 | mã đúng, còn hạn 15 phút, chưa dùng: tạo `devices`, đánh dấu mã đã dùng (cùng giao dịch, `FOR UPDATE`), trả `pair_response` |
| 400 `{"detail": "Mã ghép đôi không tồn tại hoặc đã hết hạn"}` | mã sai / hết hạn / đã dùng — **cùng một câu** để không lộ mã nào tồn tại |
| 422 | thân sai hợp đồng (mã không đủ 6 số, trường lạ…) |
| 429 + `Retry-After` | quá 10 lần thử sai/15 phút từ một nguồn (IPv6 gộp theo /64), hoặc quá 60 lần/15 phút toàn hệ thống — chặn cả khi mã đúng (đánh đổi có chủ đích: kẻ lạ làm nghẽn ghép đôi tối đa 15 phút). Mỗi lần thử giữ chỗ ngay khi vào và trả lại nếu ghép được, nên loạt yêu cầu đồng thời không lách được ngưỡng. Đếm trong bộ nhớ (một tiến trình, ADR-002); sau reverse proxy chỉ ngưỡng toàn cục có tác dụng |
| 503 | chưa cấu hình khóa ký JWT thiết bị; mã KHÔNG bị tiêu thụ |

Thành viên được bảo vệ (`role=protected`) của gia đình được tạo ở lần ghép đầu và dùng lại ở các máy sau.

**`POST /v1/consents`** — cần token thiết bị. Thân `{"items": [...]}` (1–32 mục). Chặt hơn schema chung ở hai điểm: `channel` phải là `app`, và mỗi `purpose` chỉ một lần trong một lô. `family_id`/`member_id` lấy từ token, `recorded_at` do máy chủ đặt. Trả `{"status": "recorded", "count": N, "recorded_at": "<ISO>"}`. 401 không/sai token · 422 sai hợp đồng (cả lô không ghi) · 503 DB lỗi hoặc chưa cấu hình khóa ký. Không có PUT/PATCH/DELETE (405); trigger Postgres chặn sửa/xóa ở cấp CSDL. Rút đồng ý = gửi lại `purpose` với `granted=false`.

**`GET /v1/devices/me`** — cần token thiết bị. Trả `device` (id, gia đình, nền tảng, phiên bản, mốc thời gian; KHÔNG token/băm bí mật) và `consents`: dòng mới nhất của mỗi purpose.

### Sự kiện & sự cố (spec 021 — đã có)
Hợp đồng: `events_batch.v1.json` (+ `risk_event.v1.json`), `events_result.v1.json`, `incident.v1.json` (fixture `fixtures/*.v1.*.json`).

**`POST /v1/events`** — cần token thiết bị. Thân `{"events": [RiskEvent × 1–50]}`, khớp CHẶT `risk_event.v1.json` (trường lạ, kể cả số điện thoại thô, là lỗi). `family_id`/`device_id` lấy từ token. Một lô = một giao dịch: lưu sự kiện (`ON CONFLICT (id) DO NOTHING` ⇒ gửi lại cả lô hoặc từng sự kiện đều vô hại), rồi mỗi sự kiện MỚI đi qua `IncidentService.correlate_event`. Trả `{"accepted", "duplicates", "incident_id", "incident_opened"}`.

| Mã | Khi nào |
|---|---|
| 200 | đã xử lý (kể cả khi toàn bộ là trùng: `accepted = 0`) |
| 401 | không/sai token, thiết bị bị thu hồi |
| 422 | thân sai hợp đồng — cả lô không ghi gì. Thông báo chỉ nêu vị trí + loại lỗi, KHÔNG lặp lại giá trị đã gửi. Chuỗi tự do bị ràng buộc: `app.package` dạng gói Android, `app_version`/`rules_version` dạng phiên bản (số đầu ≤ 4 chữ số, hậu tố build tùy chọn như `0.1.0-20261016`), mỗi thành phần tối đa 8 chữ số nên số điện thoại không lọt vào; số nguyên có cận trên (`duration_s` ≤ 86400, `timing.*_ms` ≤ 3.600.000); cờ boolean phải là `true/false` thật |
| 429 + `Retry-After` | thiết bị gửi quá 30 lô/phút (đếm trong bộ nhớ, một tiến trình) |
| 503 + `Retry-After` | chưa cấu hình pepper băm số điện thoại (không lưu gì), hoặc chờ khóa thiết bị quá 3 giây (lô không ghi gì, app gửi lại được) |

Mở/liên kết sự cố (FR-008): sự kiện loại `banking_app_foreground`/`flagged_number_call`/`sideload_detected`/`ask_child_pressed` hoặc `rule_floor ≥ high` mở sự cố `detected` nếu thiết bị chưa có sự cố đang mở; mọi sự kiện sau đó liên kết vào sự cố đang mở (cùng thiết bị, cùng loại thật/diễn tập, cùng `drill_id`) **còn hoạt động trong 600 giây gần nhất** (mốc = sự kiện cuối của sự cố, hoặc lúc mở nếu chưa có), và `rule_floor` cao hơn thì NÂNG `rule_floor` + `level` (không bao giờ hạ). Sự cố im lặng quá 600 giây không nhận thêm: sự kiện mới tạo sự cố MỚI (sự cố cũ giữ nguyên trạng thái; đưa nó ra khỏi `detected` thuộc bộ hẹn giờ/tác tử). Sự cố đã kết thúc không mở lại — sự kiện mới tạo sự cố mới. Số gọi đến chỉ lưu `HMAC(pepper, h1)` + 3 số cuối (ADR-006); h1 không vào DB hay log. Chưa có giới hạn kích thước thân ở tầng ứng dụng (FastAPI đọc thân trước khi xác thực) — cần giới hạn ở Caddy khi mở ra Internet.

**`GET /v1/incidents/{id}`** — cần token thiết bị; chỉ sự cố của gia đình mình, sự cố nhà khác trả 404 (không lộ sự tồn tại). Trả `incident.v1.json` kèm `transitions` (cũ → mới).
**`GET /v1/families/{id}/incidents?limit=`** — `id` phải là gia đình của token (nhà khác ⇒ 404); mới nhất trước, `limit` 1–100 (mặc định 20), bản tóm tắt không có `transitions`. Người giám hộ đọc qua `/a/{token}` (spec 022), không qua các route này.

### Câu hỏi nhanh & trả lời E8 (spec 024 — đã có)
Hợp đồng: `elder_question.v1.json`, `elder_answer.v1.json` (fixture `fixtures/*.v1.*.json`).

**`GET /v1/incidents/{id}/pending-question`** — cần token thiết bị; chỉ sự cố của gia đình mình (nhà khác ⇒ 404). Trả `elder_question.v1.json` khi đồ thị đang dừng ở `ask_elder`; `text` luôn mở đầu bằng "Đây là trợ lý AI HỏiCon." (diễn tập: kèm `[DIỄN TẬP]`), `expires_at` = mốc bộ hẹn giờ `ask_elder` (mặc định 60 s). Không có câu hỏi / sự cố đã kết thúc ⇒ 404; DB không với tới ⇒ 503 + `Retry-After`.
**`POST /v1/incidents/{id}/answers`** — cần token thiết bị; nhà khác ⇒ 404. Thân `elder_answer.v1.json`: `question_id`, `answer` ∈ `yes/no/unsure/timeout`, `note_flags` (tùy chọn) chỉ gồm cờ bool của `NOTE_KEYWORDS` (`mentions_authority/transfer/code/secrecy/app_or_link`). Không nhận văn bản tự do hay ghi âm (ADR-009). Câu trả lời KHÔNG chạy đồ thị trong request: máy chủ xếp job `graph_resume` (khóa `{id}:elder_answer` ⇒ bấm hai lần vẫn một job), worker chạy tiếp. Trả `{"status", "incident_id", "level"}`: `accepted` | `expired` (đồ thị không còn chờ câu này, hoặc `question_id` khác câu đang hỏi) | `already_resolved`; `level` là mức hiện tại của sự cố. Trả lời "Có" cho câu chuyển tiền ⇒ đồ thị nâng ít nhất `critical`; "Có" xưng cơ quan / "Không" quen người gọi ⇒ ít nhất `high` (tất định, không phụ thuộc LLM).
Đồ thị tự chạy: `POST /v1/events` mở/nâng sự cố lên `high`/`critical` ⇒ job `start_graph` (cùng ngưỡng cảnh báo nhanh; payload không h1, không tên gói). Worker là task nền trong tiến trình API (ADR-002; `HOICON_RUN_WORKER=false` khi chạy riêng). Người giám hộ quyết qua `/a/`, JWT hay Zalo ⇒ đồ thị không gửi chi tiết/nhắc T1/leo thang T2 nữa; T3 không ai trả lời ⇒ `resolved_no_response` (actor `timer`); "lừa đảo" ⇒ `case_open`.

### Tra cứu & danh sách đe dọa (spec 026 — phần server đã có; Android: làn A, chưa)
Hợp đồng: `lookup_request.v1.json`, `lookup_result.v1.json`, `threat_list.v1.json` (fixture `fixtures/*.v1.*.json`); ADR-011 (**Đề xuất**).

**`POST /v1/lookups`** — token **thiết bị** (người cao tuổi) hoặc token **người giám hộ**. Thân `lookup_request.v1.json`: `kind` ∈ `phone`/`url`, `via` ∈ `typed`/`qr`, `incident_id?`. `phone` gửi `h1` + `last3` (số thô KHÔNG bao giờ rời máy; trường lạ như `number` là 422); `url` gửi đường link ≤ 2048 ký tự. `kind=account` để dành ⇒ 422 `kind_not_supported`. Kết quả TẤT ĐỊNH theo bảng quy tắc (không LLM) và **không bao giờ `safe`** ở v1 (chưa có sổ đăng ký chính thức): `dangerous` (số trong danh sách, độ tin cậy ≥ 0,70; link tải `.apk/.xapk/.apks/.exe/.bat/.scr` ở đường dẫn hoặc chuỗi truy vấn), `warning` (số độ tin cậy thấp; link dùng IP/punycode/rút gọn, có "tên:mật khẩu@" trước host, nhắc tên ngân hàng hoặc cơ quan, `http` không TLS; dấu `\` được hiểu như `/` giống trình duyệt), `unknown` (còn lại, kể cả số chưa có trong danh sách). Trả `lookup_result.v1.json`: `reasons[]` (mã + câu tiếng Việt), `sources[]`, `disclaimer` mở đầu "Đây là trợ lý AI HỏiCon.", `incident_level` (khi có `incident_id`), `is_demo`. Không bao giờ có h1, HMAC, URL hay host trong phản hồi/log.

| Mã | Khi nào |
|---|---|
| 200 | đã tra |
| 401 | không/sai token (thiết bị bị thu hồi, thành viên không còn) |
| 403 | chưa có đồng ý `lookups` mới nhất đang `granted` của chính người gọi (`POST /v1/consents` ghi cho thiết bị) |
| 404 | `incident_id` không thuộc gia đình của token, hoặc (token thiết bị) không phải sự cố CỦA người dùng thiết bị đó (nhà khác và id lạ cùng một 404) |
| 422 | sai hợp đồng, URL không phân tích được (thông báo chỉ nêu vị trí + loại lỗi, không lặp lại đầu vào) |
| 429 + `Retry-After` | vượt hạn mức, đếm trên `verifications` (bền qua khởi động lại, đúng khi gọi đồng thời nhờ khóa tư vấn): thiết bị 20/giờ & 60/ngày, người giám hộ 60/giờ, cả gia đình 200/ngày (không tính dòng tự động của hệ thống); lần bị từ chối không được ghi |
| 503 | thiếu pepper băm, hoặc chờ khóa quá 3 giây |

Có `incident_id`: kết luận `dangerous` ⇒ NÂNG `incidents.level` lên `critical`, `warning` ⇒ `high` (`IncidentService.raise_level`: chỉ nâng, mỗi lần nâng thật tăng `version`, không đổi trạng thái; sự cố đã qua `awaiting_guardian` thì giữ nguyên). Nếu người tra là **thiết bị** và kết luận `dangerous` ⇒ xếp job `graph_resume {"evidence": verification_id}` (khóa `{incident}:evidence:{verification_id}`, nên một job bị bỏ vì đồ thị chưa chờ không đốt khóa của lần tra sau) để node `await_guardian` — node duy nhất được gửi tin — báo con đúng MỘT tin; router không gửi gì. Người giám hộ chưa có đường ghi đồng ý `lookups` (web/Zalo, spec 023/027) nên hiện bị 403.

**`GET /v1/threat-list?since=<version>`** — token thiết bị. Ảnh chụp bucket k-ẩn danh (`threat_list.v1.json`: `version`, `bucket_bits` 16–24, `count`, `buckets_b64`, `generated_at`): `bucket24 = int(h1[:6], 16)` dịch về `HOICON_THREAT_BUCKET_BITS` (mặc định 22 ≈ 86 số di động/bucket) bit đầu, bỏ trùng, sắp xếp, 3 byte/bucket (uint24 big-endian). Không có h1, HMAC hay last3. `since` trùng `version` (= `sha256(bits ‖ nội dung)[:16]`) ⇒ **304** không thân; `since` sai định dạng ⇒ 422. Loại dòng hết hạn, thiếu `bucket_enc`, không giải mã được, và dòng `is_demo` ở mọi môi trường ngoài dev/test/ci. Cache trong tiến trình 5 phút; tối đa 24 lần/ngày/thiết bị (429, đếm trong bộ nhớ); ghi `devices.threat_list_version`. Máy khớp bucket chỉ nên coi là "có thể" (khớp nhầm ≈ `N/2^bits`); kết luận chính xác luôn do máy chủ tra h1 khi nhận sự kiện.

## Người giám hộ (spec 023 — đã có)

Hợp đồng: `action_view.v1.json`, `incident_decision.v1.json` (fixture `fixtures/*.v1.*.json`).

Cảnh báo giai đoạn 1: lô sự kiện mở/nâng sự cố lên `high`/`critical` ⇒ xếp job `notify_guardian` (khóa `{incident}:msg:fast_alert`, một lần mỗi sự cố) cho người giám hộ hạng đầu. Job chỉ mang chỗ trống liên kết; token `/a/{token}` (32 byte ngẫu nhiên) sinh **lúc gửi**, chỉ lưu SHA-256 trong `action_tokens`, hạn 24 giờ, dùng một lần. Log truy cập che token (`/v1/action/***`).

**`GET /v1/action/{token}`** — không cần đăng nhập (token trong URL là chứng thực). Trả `action_view.v1.json`: `token_valid`, `scope`, `expires_at`, `used_at`, `incident` (id, state, level, rule_floor, is_drill, summary_text, protected_member_label, device_label) — không có số điện thoại hay PII.
- 200 kể cả khi token đã dùng/hết hạn/sự cố đã được xử lý qua kênh khác (`token_valid=false`) để trang báo đúng trạng thái.
- 404: token không tồn tại.

**`POST /v1/action/{token}/decision`** — không cần đăng nhập. Thân `incident_decision.v1.json`: `{"decision": "safe" | "prevented" | "false_alarm" | "emergency_pause", "note"?}`. `note` được nhận nhưng **không lưu** (chữ tự do có thể chứa PII).
- `safe`/`prevented`/`false_alarm` ⇒ `resolved_*` (kết thúc); `emergency_pause` ("nghi lừa đảo") ⇒ `case_open` (sự cố còn mở để theo dõi). Đi qua `IncidentService.transition()`; token bị khóa dòng và đánh dấu `used_at` cùng giao dịch.
- 200: `{"success": true, "incident_id", "state", "outcome"}` · 404: không có token/sự cố · 409: token đã dùng, sự cố đã được xử lý hoặc xung đột phiên bản · 410: token hết hạn · 422: `decision` sai.

**`POST /v1/incidents/{id}/decision`** — cần JWT người giám hộ (`aud=hoicon-guardian`, `role=guardian`, thành viên còn tồn tại). Thân và ánh xạ như trên. 401: thiếu/sai token · 404: sự cố không có hoặc thuộc gia đình khác · 409: đã xử lý/xung đột. Cookie `hc_guardian` cũng dùng được (kèm bằng chứng cùng nguồn, xem **CSRF** ở mục Xác thực).

**Trả lời Zalo** (ADR-010): "1" ⇒ `resolved_safe`; "2 - vẫn thấy đáng ngờ" ⇒ `case_open`; "3" gửi lại chi tiết.

### Web người giám hộ (spec 027 — đã có)

**Lệnh Zalo "4"** (hoặc "web", "đăng nhập", không phân biệt dấu/hoa thường): người giám hộ **đã ghép** nhận qua Zalo một liên kết `{HOICON_WEB_BASE_URL}/login/<token>`. Token là `action_tokens` scope `guardian_view`, không gắn sự cố, hạn **15 phút**, dùng **một lần**, chỉ lưu SHA-256; sinh ngay lúc trả lời nên không có trong `jobs.payload`/`messages_out`. Liên kết mới vô hiệu liên kết cũ chưa dùng; tối đa **5 liên kết/giờ/người** (đếm trên `action_tokens`), lần thứ 6 nhận câu từ chối nhẹ nhàng. Người chưa ghép nhận hướng dẫn ghép đôi. Tin mở đầu "Đây là trợ lý AI HỏiCon." như mọi tin Zalo.

**`POST /v1/guardian/session`** — thân `{"token"}` (`guardian_session.v1.json#/$defs/request`, 32–64 ký tự `[A-Za-z0-9_-]`). Khóa dòng token (`FOR UPDATE`), kiểm scope `guardian_view` + hạn + chưa dùng + thành viên còn là người giám hộ, đánh dấu `used_at` cùng giao dịch, rồi đặt cookie `hc_guardian`. Trả `{member_id, family_id, family_name, expires_at}` (không có token phiên trong thân, `Cache-Control: no-store`). Token sai/đã dùng/quá hạn/sai scope/mồ côi đều trả **cùng một** 410 (không lộ lý do); thân sai hợp đồng ⇒ 422 (không lặp lại đầu vào); thiếu bằng chứng cùng nguồn ⇒ 403 (token không bị đốt); thiếu khóa ký ⇒ 503 trước khi đốt token.
**`GET /v1/guardian/me`** — cùng thân như trên cho phiên hiện tại; 401 khi chưa đăng nhập hoặc thành viên đã bị xóa.
**`DELETE /v1/guardian/session`** — xóa cookie (204; vẫn 204 khi đã đăng xuất; cần bằng chứng cùng nguồn).

**`GET /v1/guardian/incidents?status=open|closed&cursor=`** — theo `incident_list.v1.json`: sự cố của gia đình trong token, **đang mở trước** (`detected/assessing/awaiting_guardian/verifying/rescore/case_open`) rồi đã xong (`resolved_*`, `closed`), mỗi nhóm mới nhất trước; 20 sự cố/trang, phân trang bằng khóa `(nhóm, opened_at, id)` nên không trùng/sót; `next_cursor` là chuỗi mờ, `null` khi hết. Mỗi mục là `IncidentSummary` + `elder_alias` (cách xưng hô, không phải tên thật) + `has_run`. `status` vắng ⇒ cả hai nhóm. 422: `status`/`cursor` sai (không lặp lại đầu vào).
**`GET /v1/guardian/incidents/{id}`** — `IncidentDetail` + `elder_alias` + `run_id` (null khi chưa có lượt chạy). Sự cố nhà khác và id lạ cùng một 404.
Dùng cùng cookie: `GET /v1/incidents/{id}/run`, `GET /v1/runs/{run_id}/steps`, `GET /v1/runs/{run_id}/stream` (trình duyệt dùng `EventSource` cùng nguồn; cookie tự gửi, tự nối lại bằng `Last-Event-ID`) và `POST /v1/incidents/{id}/decision`. Route thiết bị `/v1/incidents/*` giữ nguyên hành vi.

`/v1/families`, `/v1/case-files`, `/v1/drills` (người giám hộ) — chưa có.

## Luồng SSE & truy vết tác tử (spec 025 — đã có)

Hợp đồng: `agent_step.v1.json`, `run_steps.v1.json`, `run_done.v1.json` (fixture `fixtures/*.v1.*.json`). Chỉ đọc. Xác thực bằng JWT người giám hộ (`Authorization: Bearer …`); **không nhận token qua query string** (Caddy ghi log URL). Chưa có: `/v1/families/{id}/stream`, `/v1/demo/stream` (033/050).

**`GET /v1/runs/{run_id}/steps`** — (`Cache-Control: no-store`) lịch sử các bước đã che của lượt, theo thứ tự `(at, id)`, tối đa 500 bước: `{"run_id", "status", "is_drill", "is_demo", "steps": [agent_step…]}`.

**`GET /v1/runs/{run_id}/stream`** — `text/event-stream; charset=utf-8`, `Cache-Control: no-cache, no-transform`, `X-Accel-Buffering: no`; không có `Connection` (hop-by-hop, HTTP/2 cấm). Khung (UTF-8, `data` là JSON một dòng, mỗi khung kết thúc bằng một dòng trống):

```
retry: 3000

id: <step_id>
event: step
data: {agent_step.v1}

: ping

event: done
data: {run_done.v1}

event: error
data: {"retryable":true}
```

- `id:` chỉ có ở `event: step`. Nối lại bằng header `Last-Event-ID` = `id` của bước cuối đã nhận: server phát tiếp từ sau bước đó, không trùng; id không thuộc lượt hoặc không phải UUID ⇒ phát lại từ đầu (header rác không gây lỗi).
- `: ping` mỗi 15 s kể từ lần ghi cuối (giữ kết nối qua proxy). Server đọc DB mỗi 0,3 s nên độ trễ bước mới thường < 0,5 s.
- `done` đến đúng một lần, SAU bước cuối (lượt `done`/`failed`), rồi server đóng. Lượt `waiting` (chờ người giám hộ) không đóng luồng. Quá 600 s mà lượt chưa xong ⇒ server đóng không kèm `done`; client nối lại bằng `Last-Event-ID`.
- `error` (DB lỗi 3 nhịp liên tiếp) rồi đóng; client thử lại sau `retry`.
- Mã: 401 thiếu/sai token · 404 lượt không thấy, thuộc nhà khác hoặc là lượt eval (cùng một câu, không lộ lượt có tồn tại) · 429 người này đã mở 3 luồng hoặc cả gia đình đã mở 4 luồng · 503 tiến trình đã đủ 20 luồng (429/503 có `Retry-After`) — đều trả trước khi luồng bắt đầu. Hạn mức đếm trong bộ nhớ ⇒ đúng với một tiến trình (ADR-002).
- Bước chỉ gồm các cột trong danh sách trắng (KHÔNG có `input_redacted`); `output` qua `redact_json` (bỏ khóa `h1/hmac/phone/token/note/text/package/caller…`, hex dài ⇒ `[HASH]`, token ⇒ `[TOKEN]`, số điện thoại ⇒ `[SĐT ***xxx]`, chuỗi cắt ở 500 ký tự). `output` là `null` khi job retention đã xóa nội dung. `is_drill`/`is_demo` ở `run_steps`/`done` để giao diện gắn nhãn `[DIỄN TẬP]`.
- **Client web dùng `fetch` + đọc `ReadableStream`, không dùng `EventSource`** (không đặt được header `Authorization`). Phải tự nối lại theo `retry` và gửi `Last-Event-ID`.
- Quyền xem chỉ kiểm lúc kết nối (luồng đang mở sống tối đa 600 s). Khi tắt máy, uvicorn chờ các luồng còn mở: chạy với `--timeout-graceful-shutdown` (ví dụ 10).
- Phía sau Caddy/nginx phải tắt đệm và nén cho route này (đã có `X-Accel-Buffering: no`); đo `: ping` qua proxy thật ở spec 012.

**`GET /v1/incidents/{incident_id}/run`** — JWT người giám hộ cùng gia đình ⇒ `{"run_id", "status"}`; chưa có lượt hoặc sự cố thuộc nhà khác ⇒ 404. Đây là cách client tìm `run_id` từ sự cố.

## Webhook & khác
`POST /webhooks/zalo/{bot_id}` · `/demo/*` · `/admin/*` · `/mcp/*` (FastMCP) · `GET /healthz`

### `POST /webhooks/zalo/{bot_id}` (spec 002 — đã có)
Hợp đồng thân: `docs/schemas/zalo_update.v1.json` (fixture `fixtures/zalo_update.v1.*.json`). Không thuộc `/v1`, không sinh client TS.

| Mã | Khi nào | Job được xếp? |
|---|---|---|
| 200 `{"ok": true}` | secret đúng; kể cả cập nhật không dùng được (ảnh, nhóm, tin của bot, thiếu `message_id`, thân thử của Zalo) | chỉ khi là tin chữ riêng tư dùng được: job `zalo_update`, khóa `zalo:{bot_id}:{message_id}` ⇒ gửi lại vẫn một job |
| 400 | thân không phải JSON | không |
| 401 | secret sai/thiếu | không |
| 404 | `bot_id` không phải bot đã cấu hình (chỉ trả lời sau khi xác thực) | không |
| 413 | thân > 64 KB | không |
| 503 | chưa cấu hình secret, thiếu khóa mã hóa, hoặc DB lỗi — **Zalo nên gửi lại**; không trả 200 rồi mất cập nhật | không |

Job KHÔNG mang Zalo ID thô, tên hiển thị hay chữ người gõ (DATA-MODEL §3b). Chạy riêng cho đường hầm (chỉ route này, không
`/docs`, `/openapi.json`, `/mcp`): `uvicorn hoicon.api.webhooks:app --port 18080 --loop asyncio:SelectorEventLoop`.
Đặt/xem/xóa webhook: `python -m hoicon.ops.zalo_webhook set|info|delete` (docs/setup/ACCOUNTS.md §3).
