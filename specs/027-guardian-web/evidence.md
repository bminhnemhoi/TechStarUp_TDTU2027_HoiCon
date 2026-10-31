# Bằng chứng nghiệm thu Spec 027: Web người giám hộ

- **Trạng thái (16/10/2026)**: Làn B đã triển khai T001–T022 (chưa commit); cả hai reviewer không còn mục High chưa xử lý.
- **Môi trường đo**: Linux CachyOS, Postgres dev (cổng 15432), API uvicorn tạm cổng 18010 (khóa JWT ngẫu nhiên dùng một lần),
  web `next start` cổng 3100 (Next 16.3.8), Playwright 1.64.1 + Chromium, Zalo **mock** (chưa có token bot thật).
- **Nguồn số**: chỉ máy dev, localhost, dữ liệu hư cấu. Chưa có Caddy/VPS (thuộc 012), chưa có máy thật.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 đăng nhập qua Zalo | liên kết ≤ 5 s (mock); một lần dùng; hạn 15 phút; lỗi có hướng dẫn | `test_guardian_login.py` (17), `test_guardian_session.py` (36), `e2e/login.spec.ts` (8) | liên kết sinh ngay trong lệnh trả lời (test giới hạn ≤ 5 s đạt); token một lần (lần hai ⇒ 410), hạn 15 phút (đo trong DB: 14:50–15:10), mọi lỗi cùng một 410 + trang báo lỗi tiếng Việt kèm "Nhắn số 4" | ĐẠT (Zalo mock) |
| SC-002 cô lập gia đình | 0 truy cập chéo (404); thành viên bị xóa ⇒ 401 | `test_guardian_incidents.py` (16): ma trận 2 gia đình × `/v1/guardian/incidents/{id}`, `/v1/incidents/{id}/run`, `/v1/runs/{id}/steps`, `/v1/runs/{id}/stream`, `POST /v1/incidents/{id}/decision` | nhà khác và id lạ cùng một 404 (thân giống hệt) ở mọi route; quyết định nhắm nhà khác không đổi trạng thái; xóa người giám hộ ⇒ 401 ngay | ĐẠT |
| SC-003 bảo mật phiên | cờ cookie đúng; POST bằng cookie thiếu Origin ⇒ 403; 0 token thô trong log, `jobs`, `messages_out` | `test_guardian_session.py`, `test_guardian_login.py` (quét `jobs`, `messages_out`, `action_tokens`, `caplog`), `e2e/login.spec.ts` | cookie `HttpOnly; SameSite=Strict; Path=/v1; Max-Age=604800`, thêm `Secure` ở env ngoài dev/test/ci (kiểm với `prod`, `production`, `staging`, rỗng); 6 kiểu thiếu bằng chứng cùng nguồn ⇒ 403 và không đổi gì; token không có trong DB/log/`jobs`/`messages_out`; trang `/login/*` có `Referrer-Policy: no-referrer`, `X-Robots-Tag: noindex`, `<meta robots/referrer>`; URL bỏ token trước lời gọi API (đo bằng `page.url()` lúc POST) | ĐẠT |
| SC-004 trace trực tiếp | bước mới hiện ≤ 1 s; nối lại không trùng; `done` ⇒ "Trợ lý AI đã làm xong các bước" | `e2e/live.spec.ts` (API + DB dev thật), `e2e/detail.spec.ts` (luồng giả) | live, 3 bước chèn liên tiếp (hai lần chạy): **103, 110, 64 ms** và **247, 244, 264 ms** từ lúc chèn vào DB tới lúc hiện trên trang (thăm dò DB mỗi 0,3 s); luồng giả: bỏ trùng theo `id`, nối lại sau khi mất kết nối ("Đang kết nối lại…" rồi "Đã xong") không trùng bước, sau `done` không mở lại luồng | ĐẠT (localhost) |
| SC-005 UX & khả năng tiếp cận | ảnh 360/768/1280 px + 200%, không tràn; axe 0 lỗi serious/critical; nút chính ≥ 64 px | `e2e/a11y.spec.ts`: 4 màn hình × 5 cỡ (360/768/1280 + chữ 200% ở 360 và 1280) = 20 ảnh | 20/20 đạt: không tràn ngang, chữ ≥ 16 px, mọi `a`/`button` ≥ 44 px, nút chính ≥ 64 px, axe 0 serious/critical **kể cả `color-contrast-enhanced` (7:1)**; ảnh ở `~/hoicon-evidence/027-guardian-web/` | ĐẠT (reviewer UX: 0 Chặn, 4 Cao đã sửa) |
| SC-006 hợp đồng & hồi quy | schema có test; client TS sinh lại; web lint/typecheck/build xanh; pytest không hỏng | CI + lệnh T021 | `test_guardian_schemas.py` 8/8; `gen-api-client.sh` + `typecheck` xanh; `pnpm lint`/`typecheck`/`build` xanh; pytest toàn bộ **1597 passed** | ĐẠT |

## Next 16 và SSE (T003–T004)

**T003: đọc tài liệu Next 16.3.8** (`node_modules/next/dist/docs/01-app/03-api-reference/…`):
- `compress`: `next start` nén gzip mặc định cho nội dung kết xuất và tệp tĩnh. Nén chỉ áp khi phản hồi không có
  `Cache-Control: no-transform`; API (025) đã đặt `no-cache, no-transform` cho luồng.
- `rewrites`: rewrite hoạt động như proxy URL (kể cả tới URL ngoài). Rewrite dạng mảng chạy sau route tĩnh và
  trước route động, nên route handler dự phòng (nếu cần) phải là route tĩnh dưới `/v1`.
- `route.md`: route handler trả được `ReadableStream`/`Response` bất kỳ; không cần dùng ở đây.

**T004: đo thật (16/10/2026, máy dev, localhost, `next start` 16.3.8 build với `HOICON_API_URL` trỏ tới API tạm)**:
`sse_probe` chèn 5 dòng `agent_steps` (cách nhau 1 s) vào một lượt `running`, đo từ lúc commit tới khi khung `data:` có
đúng `id` bước đó xuất hiện. Client gửi `Accept-Encoding: gzip`.

| Đường | Status | `Content-Type` | `Content-Encoding` | Độ trễ 5 lần (ms) | Tối đa |
|---|---|---|---|---|---|
| API trực tiếp (`:18010`) | 200 | `text/event-stream; charset=utf-8` | không | 27, 122, 147, 216, 238 | 238 ms |
| Qua rewrite của Next (`:3100`) | 200 | `text/event-stream; charset=utf-8` | không | 31, 123, 147, 215, 241 | 241 ms |

**Lựa chọn: giữ rewrite, dùng `EventSource` cùng nguồn; KHÔNG làm route handler dự phòng.** Rewrite không đệm hay nén
luồng (≤ 241 ms < 1 s, không có `Content-Encoding`). Giới hạn của phép đo: xác thực bằng Bearer (cookie `hc_guardian`
chưa có lúc đo; cách truyền danh tính không ảnh hưởng tới việc đệm), và chưa đo qua Caddy (thuộc 012).

## Lệnh đã chạy (16/10/2026, sau các sửa của reviewer)

| Lệnh | Kết quả |
|---|---|
| `pytest` toàn bộ (`uv run --directory backend pytest`) | **1597 passed** (riêng 027: session 36, login 17, incidents 16, ops 6, schema 8, inbound/texts) |
| `ruff check` + `ruff format --check` (`src/ tests/`) | sạch, 163 tệp đúng định dạng |
| `pnpm --dir apps/web lint` / `typecheck` / `build` | xanh |
| `pnpm --dir apps/web e2e` (Playwright, Chromium) | **58 passed, 1 skipped** (`live` tự bỏ qua khi thiếu `HOICON_E2E_LIVE`): login 8, incidents 10, detail 20, a11y 20 |
| `HOICON_E2E_LIVE=1 pnpm --dir apps/web e2e live` (API + DB dev thật, hai lần) | passed cả hai; độ trễ bước mới: lần 1 **103/110/64 ms**, lần 2 (sau sửa UX) **247/244/264 ms** — tối đa 264 ms < 1 s (thăm dò DB 0,3 s nên dao động 0–300 ms) |
| gitleaks từng thư mục (`backend/src`, `backend/tests`, `apps/web/src`, `apps/web/e2e`, `docs/schemas`, `specs/027-guardian-web`) với `.gitleaks.toml` của repo | 0 rò rỉ (không dùng cấu hình repo, `docs/schemas/fixtures/device_me.v1.invalid.json` — tệp có từ spec 020 — bị cờ `generic-api-key` vì là băm giả; không phải do 027) |
| `python3 scripts/check-spec-trace.py` | 17 spec, 0 lỗi |
| Đột biến backend (9) | cả 9 bị test bắt: bỏ kiểm Origin (9 đỏ), SameSite=lax (1), không Secure (4), token không bị đốt (2), bỏ lọc gia đình ở danh sách (4) và chi tiết (2), không vô hiệu link cũ (3), bỏ hạn mức 5/giờ (1), không bỏ dấu "đ" (3) |
| Đột biến web (5) | cả 5 bị test bắt: bỏ `replaceState` (2 đỏ), bỏ dedupe theo id (2), bỏ bước xác nhận (3), `tel:` kèm số (1), nút thấp 40 px (6) |
| Kiểm axe có thực sự bắt lỗi | trang thử có chữ #767676/#fff 20 px và ảnh thiếu alt: axe báo `color-contrast-enhanced` (serious) và `image-alt` (critical) |
| T004 SSE | xem mục "Next 16 và SSE" |

## Review độc lập

**`security-privacy-reviewer` (xác thực, 16/10/2026): 0 Critical, 0 High, 4 Medium, 6 Low.** Đã xử lý (test đỏ trước):
- #5 thử lại sau lỗi Zalo tạm thời không đốt hạn mức 5/giờ (token lần hỏng bị thay, không cộng dồn);
- #6 tin liên kết đăng nhập là tin khẩn nên không bị `held_quota`; #7 `guardian_view` gắn sự cố không đổi được thành phiên (410, không đốt);
- #9 fixture không còn chuỗi giống số di động; #10 mô tả OpenAPI/docstring của 025 nói đúng về cookie + `EventSource`;
- #2 (một phần): e2e kiểm thật `Cache-Control: no-store`, `X-Robots-Tag`, `Referrer-Policy` trên `next start`;
- #1 (một phần): cảnh báo khi khởi động nếu `HOICON_ENV` thuộc dev mà `HOICON_WEB_BASE_URL` là https; `docs/API.md` nói rõ giới hạn thu hồi.

Để lại, đã ghi ROADMAP "Ghi chú" (cần Tiến/Minh quyết): #1 cờ `Secure` phụ thuộc `HOICON_ENV` (mặc định `dev`); #2 đổi sang fragment
`/login#<token>`; #3 thu hồi phiên thật (cần migration, ngoài phạm vi 027) và SSE không kiểm lại thành viên; **#4 đồng ý
`guardian_alerts` có bao gồm xem lại lịch sử trên web không (DPIA, luật 7)**; #8 web nhận thừa `device_id`, `drill_id`, `version`.

**`ux-elder-reviewer` (ảnh + câu chữ, 16/10/2026): 0 Chặn, 4 Cao, nhiều Trung bình/Thấp.** Cả 4 mục Cao đã sửa:
- nút gọi đổi thành "Mở bàn phím gọi điện" kèm lưu ý "HỏiCon không lưu số điện thoại" (vẫn `tel:` không số);
- hành động lên cao: ở 360 px nút "Gọi", "Đã gọi được" và "Tôi nghi … đang bị lừa" nằm trong màn hình đầu 800 px (test đo);
- ở chữ 200% thẻ rủi ro gọn hơn (bỏ ngày giờ đầy đủ, chỉ còn "Mở … trước"; ngày giờ ở mục Lịch sử);
- diễn tập: câu xác nhận và "Đã ghi nhận" nói rõ "chỉ là bài tập, không có nguy hiểm thật", không bao giờ "nhắc không chuyển tiền".
Đã sửa thêm: "vừa xong" ⇒ "mở vừa xong", sự cố đã xong dùng khung trung tính + "Mức rủi ro lúc đó", câu xác nhận nêu hệ quả + chuyển tiêu điểm,
nút "Tôi nghi {tên} đang bị lừa", phiên hết hạn ⇒ `/login?het-han=1` có lời giải thích, lỗi liên kết dạng gạch đầu dòng + nút về hướng dẫn,
huy hiệu `rounded-2xl`, biểu tượng `aria-hidden`, câu trace đầy đủ thay cho chuỗi chấm phẩy, thứ tự bước cùng thời điểm theo trình tự node,
"người thân" chữ thường giữa câu. Còn lại (Trung bình/Thấp, ghi ROADMAP): `case_open` chưa có nút "đã rõ an toàn" (cần quy tắc
chuyển trạng thái), đổi "sự cố" thành "cảnh báo", màu nút khóa đạt 7:1. Chưa xem được: trạng thái đang tải/đang gửi, nhãn TalkBack thật.

## Còn mở (không đánh ☑ ở nơi khác)

- Zalo là **mock** (chưa có token bot): liên kết đăng nhập chưa gửi qua Zalo thật; cách Zalo xem trước liên kết (có thể "đốt" token) chưa kiểm.
- Chưa có Caddy/VPS (012): che log `/login/*`, `/a/*` và định tuyến `/v1/*` chưa kiểm; chưa chạy CI trên PR; chưa chạy Windows.
- Web chưa thử trên điện thoại thật; ảnh/đo chỉ ở Chromium desktop giả lập kích thước.
