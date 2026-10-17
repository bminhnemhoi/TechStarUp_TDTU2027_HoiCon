# Kế hoạch Spec 027: Web người giám hộ

**Mã**: `027-guardian-web` · **ROADMAP**: `P2-12` · **Làn**: B · Spec: [`spec.md`](spec.md)

## 1. Kiểm theo hiến chương

| Nguyên tắc | Áp dụng |
|---|---|
| II. Riêng tư | Không PII trên web; token đăng nhập chỉ lưu SHA-256, không vào `jobs`/log; cookie HttpOnly; không dùng `localStorage` |
| IV. Công khai AI | Tin Zalo có liên kết đăng nhập đi qua `deliver`; khối nội dung do máy sinh trên web có câu công khai |
| V. Hợp đồng trước | `guardian_session.v1`, `incident_list.v1` + fixture viết trước; sinh lại client TS |
| VI. UX | Web người giám hộ (người trưởng thành, không phải app người cao tuổi): chữ ≥ 16 px, vùng chạm ≥ 44 px, nút chính ≥ 64 px, tương phản ≥ 7:1 theo token, 200% không tràn |
| VII. Bằng chứng trung thực | Số độ trễ là localhost; Zalo là mock (chưa có token bot) |
| VIII. Tái sử dụng | `action_tokens` (scope `guardian_view` sẵn có), `ActionTokenService`, `ACTION_LINK_SLOT`/`_fill_action_link`, `deliver`, `apply_guardian_decision`, `IncidentDetail`, `tokens.css`, mẫu trang `/a/[token]` |

## 2. Quyết định kiến trúc

### D1. Đăng nhập bằng liên kết một lần gửi qua chính Zalo đã ghép

| Phương án | Ưu | Nhược | Kết luận |
|---|---|---|---|
| **A. Nhắn "4" ⇒ liên kết `/login/<token>` qua Zalo** | Dùng đúng danh tính đã ghép (Zalo); không thu thêm dữ liệu; tái dùng `action_tokens` + `deliver` | Mỗi lần đăng nhập tốn 1 tin trong hạn mức 3.000 tin/tháng | **chọn**. Phiên 7 ngày nên số tin rất ít |
| B. Đổi token `/a/` lấy phiên | Không tốn tin | Token `/a/` gắn một sự cố, dùng một lần cho **quyết định**; ai cầm tin cảnh báo cũng vào được toàn bộ lịch sử gia đình | loại (mở rộng quyền ngoài mục đích) |
| C. Email/mật khẩu, OTP SMS | Quen thuộc | Thu thêm PII, cần mục đích đồng ý mới, chi phí SMS, mất thời gian | loại |

Chi tiết:
- **Token:** `secrets.token_urlsafe(32)`, chỉ lưu SHA-256, hạn 15 phút, dùng một lần. Sinh lúc gửi qua chỗ trống của 023,
  nên `jobs.payload` chỉ có chỗ trống.
- **Liên kết mới vô hiệu liên kết cũ.** Tạo liên kết mới thì đặt `used_at = now()` cho các token `guardian_view` chưa dùng
  của cùng người, để mỗi lúc chỉ có một liên kết sống.
- **Hạn mức:** 5 lần/giờ/người, đếm trên `action_tokens` (bền).
- **Phiên:** JWT người giám hộ sẵn có (`aud=hoicon-guardian`), hạn 7 ngày, trong cookie `hc_guardian`
  (`HttpOnly; Secure; SameSite=Strict; Path=/v1`). Ở dev qua `http://localhost`, cờ `Secure` tắt có điều kiện theo
  `HOICON_ENV=dev`.
- **Thu hồi:** `get_current_guardian` đã kiểm thành viên còn tồn tại với role `guardian` ở mỗi request. Xóa thành viên là
  phiên mất hiệu lực ngay, không cần danh sách đen.

### D2. Danh tính cho luồng SSE: cookie cùng nguồn + `EventSource`, dự phòng route handler

- Spec 025 viết cho client gửi header Bearer bằng `fetch`, nhưng bản thân 025 không cấm cookie.
- Với cookie HttpOnly cùng nguồn (`/v1/*` qua rewrite), `EventSource` gửi cookie tự động, tự nối lại theo `retry` và tự
  gửi `Last-Event-ID`. Ít code hơn tự viết bộ đọc `fetch`.
- **Rủi ro chưa kiểm:** rewrite của Next 16 khi chạy `next start` có thể nén gzip hoặc đệm phản hồi `text/event-stream`.
  T004 đo điều này trước khi viết giao diện.
  - Nếu có đệm: thêm route handler tĩnh `app/v1/web-stream/route.ts` (`?run=<run_id>`), gọi API bằng `fetch` (gắn Bearer
    lấy từ cookie phía máy chủ), trả nguyên `ReadableStream` với `Content-Encoding: identity`; client `EventSource` trỏ
    vào route đó. Hai ràng buộc:
    - Đặt dưới `/v1`, vì cookie `Path=/v1` không được gửi tới `/v1-stream` (sau tiền tố phải là `/` hoặc hết chuỗi).
    - Phải là route tĩnh, vì rewrite dạng mảng của Next 16 chạy trước route động (`rewrites.md`: "after checking the
      filesystem … and before dynamic routes").
  - Ở prod, Caddy có thể định tuyến thẳng `/v1/*` tới API, không qua Next. 012 quyết, plan này ghi lại.
- **CSRF:** cookie `SameSite=Strict`, cộng thêm kiểm `Origin`/`Sec-Fetch-Site` cho lệnh ghi khi xác thực bằng cookie
  (phòng thủ chiều sâu, vì trình duyệt cũ có thể bỏ qua `SameSite`).

### D3. Route đọc riêng `/v1/guardian/*`, không trộn vào route thiết bị

- `GET /v1/incidents/{id}` của thiết bị đã có test và hợp đồng. Thêm nhánh "hoặc người giám hộ" vào cùng dependency làm
  ma trận quyền khó kiểm.
- Vì vậy dùng prefix riêng `/v1/guardian/` với `get_current_guardian`, dùng lại model `IncidentSummary`/`IncidentDetail`
  và cùng truy vấn (tách hàm `_load_incident(session, id, family_id)` dùng chung).
- `POST /v1/incidents/{id}/decision` (023) giữ nguyên đường dẫn và nhận thêm cookie nhờ FR-003.

### D4. Không thêm shadcn/ui ở spec này

Repo chưa dùng shadcn. Luật toàn cục: "chỉ nạp `shadcn` cho dự án đã dùng hoặc đã chọn". 4 trang này dựng được bằng
Tailwind + `tokens.css` theo đúng mẫu của `/a/[token]`. Việc chọn shadcn để dành cho 033 (dashboard nhiều thành phần), ghi
vào ROADMAP "Ghi chú".

### D5. Kiểm thử web: Playwright chặn mạng bằng fixture hợp đồng, cộng một kịch bản chạy với API thật

- CI web hiện không có Postgres. Bài test chặn `/v1/*` bằng `page.route` trả fixture trong `docs/schemas/fixtures/`; luồng
  SSE giả là một phản hồi `text/event-stream` dựng sẵn. Như vậy test tất định, chạy được trong job `web` hiện có.
- Kịch bản `live.spec.ts` (bỏ qua nếu thiếu `HOICON_E2E_LIVE=1`) chạy với API + DB dev: sinh token đăng nhập bằng lệnh ops,
  đăng nhập, xem danh sách, chèn bước vào `agent_steps`, thấy bước hiện lên, rồi quyết định. Bằng chứng SC-004 lấy từ
  kịch bản này.

## 3. Luồng

```
Zalo: người giám hộ nhắn "4"
  → webhook → job zalo_update → classify = login → (đã ghép?) → ActionTokenService.issue(scope=guardian_view, ttl=15')
  → deliver(texts.guardian_login_link, slot) ─► Zalo: "Đây là trợ lý AI HỏiCon. Liên kết đăng nhập (15 phút, dùng 1 lần): https://…/login/<token>"
Trình duyệt: /login/<token> → replaceState('/login') → POST /v1/guardian/session {token}
  → khóa dòng token, kiểm, used_at → Set-Cookie hc_guardian=<JWT 7 ngày>  → /incidents
/incidents → GET /v1/guardian/incidents?status=open|closed
/incidents/[id] → GET /v1/guardian/incidents/{id} (+ run_id) → GET /v1/runs/{run_id}/steps → EventSource /v1/runs/{run_id}/stream
  → hành động → POST /v1/incidents/{id}/decision (cookie + Origin) → apply_guardian_decision → IncidentService
```

## 4. Hợp đồng (phác thảo, Draft 2020-12, `additionalProperties: false`)

```json
// guardian_session.v1.json
{"$defs": {
  "request":  {"required": ["token"], "properties": {"token": {"type": "string", "pattern": "^[A-Za-z0-9_-]{32,64}$"}}},
  "response": {"required": ["member_id","family_id","family_name","expires_at"],
               "properties": {"member_id": {"format": "uuid"}, "family_id": {"format": "uuid"},
                              "family_name": {"type": "string", "maxLength": 64}, "expires_at": {"format": "date-time"}}}}}
// incident_list.v1.json
{"required": ["incidents","next_cursor"], "properties": {
  "incidents": {"type": "array", "items": {"$ref": "incident.v1.json#/$defs/summary"}},
  "next_cursor": {"type": ["string","null"], "maxLength": 128}}}
```

Nếu `incident.v1.json` chưa có `$defs/summary`, T001 thêm vào và giữ tương thích ngược (thêm trường tùy chọn
`elder_alias`, `has_run`).

## 5. Bảng dịch bước trace sang tiếng Việt (cố định, không LLM)

| `node` | Câu hiển thị | Lấy từ `output` |
|---|---|---|
| `ingest` | "Nhận tín hiệu từ điện thoại của {alias}" | `level` ⇒ "mức ban đầu: …"; `threat = flagged` ⇒ "số gọi đến có trong danh sách cảnh báo" |
| `fast_alert` | "Đã gửi cảnh báo nhanh cho người nhà" | — |
| `risk_scorer` | "Đánh giá mức rủi ro" | `level`; `question` ⇒ "sẽ hỏi {alias} một câu ngắn" |
| `ask_elder` | "{alias} đã trả lời câu hỏi" / "{alias} chưa trả lời" | chỉ enum câu trả lời; không hiện văn bản |
| `verification` (026) | "Kiểm tra số/đường link trong danh sách cảnh báo" | `dangerous`/`warning` (số lượng) |
| `intervention` | "Gửi tóm tắt cho người nhà" | `skipped` ⇒ "bỏ qua vì đã có người quyết" |
| `await_guardian` | "Đang chờ người nhà quyết định" / "Đã nhắc lại" / "Đã báo người nhà thứ hai" | `resumed_with` |
| `resolve` | "Kết thúc: {kết cục tiếng Việt}" | `outcome` |
| khác | "Bước khác của trợ lý AI" | — |

Mức rủi ro: `low` "Thấp", `medium` "Trung bình", `high` "Cao", `critical` "Rất cao". Mỗi mức kèm biểu tượng riêng
(không chỉ dựa vào màu).

## 6. Bản đồ file

| File | Thay đổi |
|---|---|
| `docs/schemas/guardian_session.v1.json`, `incident_list.v1.json` (+ `incident.v1.json` nếu cần) + fixtures | mới/sửa |
| `backend/src/hoicon/api/auth.py` | cookie trong `get_current_guardian`, kiểm Origin cho lệnh ghi, `GUARDIAN_WEB_TTL` |
| `backend/src/hoicon/api/routers/guardian.py` | mới: session, me, incidents |
| `backend/src/hoicon/api/routers/incidents.py` | tách `_load_incident` dùng chung |
| `backend/src/hoicon/channels/inbound.py` (phân loại) + `channels/updates.py` (xử lý) | lệnh `login` |
| `backend/src/hoicon/agents/texts.py` | `guardian_login_link`, `login_not_paired` |
| `backend/src/hoicon/config.py` | danh sách `web_origins` cho kiểm Origin |
| `apps/web/src/app/login/page.tsx`, `login/[token]/page.tsx`, `incidents/page.tsx`, `incidents/[id]/page.tsx`, `src/lib/{api,stream,steps}.ts` | mới |
| `apps/web/e2e/*.spec.ts`, `playwright.config.ts`, `package.json` (devDeps, script `e2e`) | mới |
| `.github/workflows/web.yml` | thêm bước `pnpm e2e` (Chromium) |
| tests backend: `integration/test_guardian_login.py`, `integration/test_guardian_session.py`, `integration/test_guardian_incidents.py`, `contract/test_guardian_schemas.py` | mới |

## 7. Giai đoạn

1. **Hợp đồng:** schema + fixture + test.
2. **Kiểm rủi ro:** đo rewrite của Next với luồng SSE (D2) trước khi chọn client.
3. **Máy chủ:** liên kết đăng nhập, phiên, CSRF, route đọc, sinh lại client TS.
4. **Web:** 4 trang + hook luồng + bảng dịch bước.
5. **Kiểm thử:** Playwright có chặn mạng, axe, 3 kích thước, 200%; kịch bản chạy với API thật.
6. **Tài liệu và nghiệm thu.**

## 8. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Rewrite của Next đệm SSE | T004 đo trước; có phương án route handler |
| Token `/login/<token>` nằm trong đường dẫn ⇒ lọt vào log truy cập của Caddy/Next khi chạy prod | Hạn 15 phút + một lần dùng; bộ lọc log API (023) che cả `/login/`; 012 phải cấu hình Caddy che `/login/*` và `/a/*` (ghi vào ROADMAP "Ghi chú") |
| Liên kết đăng nhập bị chuyển tiếp cho người khác | Hạn 15 phút, một lần dùng, liên kết mới vô hiệu liên kết cũ; trang `/incidents` hiện tên gia đình để người dùng nhận ra |
| Hạn mức Zalo | 5 liên kết/giờ/người; phiên 7 ngày; tin đăng nhập là tin trả lời, đếm như các tin khác (ADR-010) |
| Cookie `Secure` trên `http://localhost` khi dev | Tắt `Secure` có điều kiện `HOICON_ENV=dev`; có test bảo đảm prod luôn bật |
| Trình duyệt cũ bỏ qua `SameSite` | Kiểm `Origin`/`Sec-Fetch-Site` cho mọi lệnh ghi bằng cookie |
| Bảng dịch bước lệch khi đồ thị thêm node (026) | Khóa lạ ⇒ "Bước khác"; test có một node lạ |
