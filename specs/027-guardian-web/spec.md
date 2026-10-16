# Spec 027: Web người giám hộ (danh sách, chi tiết sự cố, trace trực tiếp)

**Mã ROADMAP**: `P2-12` · **Làn**: B (`backend/**`, `apps/web/**`) · **Cột mốc**: Gate M2
· **Phụ thuộc**:
- `023-guardian-alert`: `/a/[token]`, `POST /v1/incidents/{id}/decision` (JWT người giám hộ), `action_tokens`.
- `025-trace-sse`: `/v1/runs/{id}/steps`, `/v1/runs/{id}/stream`, `/v1/incidents/{id}/run`.
- `002-zalo-guardian-channel`: bot Zalo, `deliver` qua `messages_out`.

· **Nhánh**: `feat/027-guardian-web` · **ADR**: ADR-003/010 (kênh Zalo), ADR-006

---

## 1. Bối cảnh

Người giám hộ hiện chỉ có tin Zalo và trang `/a/[token]` gắn với **một** sự cố. Họ chưa thể xem lại các sự cố cũ, theo
dõi trợ lý AI đang làm gì, hay quyết định khi liên kết `/a/` đã hết hạn. Hiện trạng đã đọc ngày 16/10/2026:

| Thành phần | Hiện trạng | Hệ quả |
|---|---|---|
| Đăng nhập người giám hộ | `issue_guardian_access_token` có trong `api/auth.py` nhưng **không route nào cấp**. `docs/API.md` ghi "đăng nhập web — spec 027" | Đây là nhánh rẽ kiến trúc chính của spec (plan D1) |
| Danh tính người giám hộ | `members.role = 'guardian'`, ghép qua Zalo `/start <mã>`; chỉ lưu HMAC Zalo ID + `chat_enc` (không email, không số điện thoại) | Không có mật khẩu, email hay OTP SMS. Kênh xác thực duy nhất đang có là **chính tài khoản Zalo đã ghép** |
| `action_tokens` | Scope cho phép: `incident_decision`, `guardian_view`, `drill_debrief`; `incident_id` cho phép rỗng; chỉ lưu SHA-256 | `guardian_view` + `incident_id` rỗng dùng được làm liên kết đăng nhập một lần, **không cần migration** |
| `GET /v1/incidents/{id}`, `GET /v1/families/{id}/incidents` | Chỉ nhận JWT **thiết bị** | Cần cho người giám hộ đọc được (FR-004) |
| Trace (025) | JWT người giám hộ qua header Bearer; cấm token trong query | Web cần cách gửi danh tính cho luồng SSE (plan D2) |
| `apps/web` | Next.js 16.3.8, React 19, Tailwind v4, `tokens.css` sinh từ `tokens.json`; rewrite `/v1/*` sang API; **chưa có** shadcn/ui, Playwright hay bất kỳ test web nào | Không thêm shadcn trong spec này (plan D4). Thêm Playwright vì CLAUDE.md luật 16 đòi ảnh chụp |
| Trạng thái sự cố | `detected`, `assessing`, `awaiting_guardian`, `verifying`, `rescore`, `case_open`, `closed`, `resolved_{safe,prevented,false_alarm,no_response}` | Bản giao việc nêu `pending_guardian`, `closed_dismissed`: **không tồn tại**, nên spec dùng đúng tên trạng thái thật |
| Nút "Gọi cho bố/mẹ" | Máy chủ không có số điện thoại (ADR-006). `/a/` dùng `tel:` không kèm số (mở bàn phím gọi) | Web làm giống `/a/`; không bao giờ có số trong trang |

## 2. User story

| # | Ưu tiên | Câu chuyện |
|---|---|---|
| US-12.1 | **P1** | Là con, tôi nhắn "4" cho bot HỏiCon trên Zalo, nhận liên kết đăng nhập dùng một lần, bấm vào là vào được web của gia đình mình |
| US-12.2 | **P1** | Là con, tôi thấy danh sách sự cố của gia đình (đang mở trước), mỗi sự cố có mức rủi ro bằng màu + biểu tượng + chữ, có nhãn `[DIỄN TẬP]` nếu là diễn tập |
| US-12.3 | **P1** | Là con, tôi mở một sự cố, thấy lịch sử chuyển trạng thái và các bước của trợ lý AI cập nhật trực tiếp, rồi quyết định "An toàn" / "Nghi lừa đảo" / "Báo nhầm" |
| US-12.4 | **P2** | Là con, tôi đăng xuất được, và phiên tự hết hạn; người giám hộ bị gỡ khỏi gia đình thì phiên mất hiệu lực ngay |

## 3. Tiêu chí thành công

| Mã | Tiêu chí | Ngưỡng | Nguồn đo |
|---|---|---|---|
| **(SC-001)** | Đăng nhập qua Zalo | Từ lúc nhắn "4" tới khi vào được `/incidents`: liên kết đến qua Zalo mock ≤ 5 s ở máy chủ (đo trong test); token dùng một lần, hết hạn sau 15 phút, dùng lại hoặc quá hạn ⇒ trang báo lỗi tiếng Việt kèm hướng dẫn | pytest + Playwright |
| **(SC-002)** | Cô lập gia đình | 0 truy cập chéo: mọi route đọc/ghi mới với sự cố, lượt chạy hoặc gia đình khác ⇒ 404; phiên của thành viên đã bị xóa ⇒ 401 | pytest tích hợp (ma trận route × 2 gia đình) |
| **(SC-003)** | Bảo mật phiên | Cookie `HttpOnly; Secure; SameSite=Strict; Path=/v1`; lệnh ghi (POST) dùng cookie mà thiếu `Origin` cùng nguồn ⇒ 403; token đăng nhập không có trong log truy cập, `jobs`, `messages_out.text` (chỉ có trong tin Zalo đã gửi); trang có token đặt `noindex` + `no-referrer` | pytest + Playwright + quét DB/log |
| **(SC-004)** | Trace trực tiếp | Trên trang chi tiết, bước mới của đồ thị hiện ≤ 1 s sau khi được commit (localhost); mất kết nối thì tự nối lại không trùng bước; lượt `done` thì hiện "Đã xong" | Playwright với API thật (local) + test dùng luồng giả |
| **(SC-005)** | UX & khả năng tiếp cận | Ảnh Playwright ở 360 px, 768 px, 1280 px và cỡ chữ 200% cho 4 trang (đăng nhập, danh sách, chi tiết, lỗi): không tràn ngang; chữ ≥ 16 px (web người giám hộ, không phải app người cao tuổi), vùng chạm ≥ 44 px, nút chính ≥ 64 px; axe-core 0 vi phạm `serious`/`critical`; tương phản ≥ 7:1 cho chữ thân (token) | Playwright + `@axe-core/playwright` |
| **(SC-006)** | Hợp đồng & hồi quy | Schema mới có fixture và test; client TS sinh lại; `pnpm --dir apps/web lint typecheck build` xanh; pytest toàn bộ không hỏng test cũ | CI |

## 4. Yêu cầu chức năng

- **(FR-001)** Hợp đồng trước, viết trong `docs/schemas/` kèm fixture `valid`/`invalid` và test hợp đồng:
  - `guardian_session.v1.json` (vào: `{"token"}`; ra: `{"member_id", "family_id", "family_name", "expires_at"}`).
    Không có số điện thoại, Zalo ID hay token phiên trong thân phản hồi; token phiên chỉ nằm trong cookie.
  - `incident_list.v1.json`: dạng `IncidentSummary` hiện có, thêm `elder_alias`, `has_run`, `next_cursor`.
- **(FR-002)** Liên kết đăng nhập qua Zalo:
  - Bot nhận "4" hoặc "web" / "đăng nhập" (không phân biệt dấu) từ người giám hộ **đã ghép**.
  - Bot tạo `action_tokens` scope `guardian_view`, `incident_id` rỗng, hạn 15 phút, chỉ lưu SHA-256.
  - Bot trả lời qua `deliver` (`messages_out`, hạn mức, mở đầu bằng "Đây là trợ lý AI HỏiCon") bằng liên kết `/login/<token>`.
  - Token được sinh lúc gửi theo đúng cơ chế chỗ trống của 023 (`ACTION_LINK_SLOT`), nên không nằm trong `jobs.payload`.
  - Người chưa ghép nhắn "4" ⇒ trả lời hướng dẫn ghép đôi.
  - Mỗi người tối đa 5 liên kết/giờ; liên kết mới làm liên kết cũ chưa dùng hết hiệu lực.
- **(FR-003)** Phiên web:
  - `POST /v1/guardian/session` đổi token lấy phiên:
    - khóa dòng token, kiểm scope/hạn/chưa dùng, đánh dấu `used_at` trong cùng giao dịch;
    - đặt cookie `hc_guardian` = JWT người giám hộ hạn 7 ngày (`GUARDIAN_WEB_TTL`);
    - token sai/đã dùng/quá hạn đều trả 410 với **cùng** thông điệp (không lộ lý do).
  - `GET /v1/guardian/me` trả thông tin phiên.
  - `DELETE /v1/guardian/session` xóa cookie.
  - `get_current_guardian` nhận Bearer **hoặc** cookie. Khi xác thực bằng cookie, mọi phương thức không an toàn đòi
    `Origin` khớp danh sách cho phép, hoặc `Sec-Fetch-Site: same-origin`; nếu không ⇒ 403.
- **(FR-004)** API đọc cho người giám hộ:
  - `GET /v1/guardian/incidents?status=open|closed&cursor=` theo `incident_list.v1`, phân trang bằng khóa
    `(opened_at, id)`, 20 sự cố/trang, đang mở trước.
  - `GET /v1/guardian/incidents/{id}` dùng lại `IncidentDetail` hiện có, thêm `elder_alias` và `run_id?`.
  - Chỉ trong `claims.family_id`; nhà khác ⇒ 404.
  - Route thiết bị hiện có giữ nguyên hành vi.
- **(FR-005)** Trang `/login/[token]`:
  - Đọc token từ đường dẫn rồi **ngay lập tức** thay URL bằng `/login` (`history.replaceState`) trước khi gọi API, để
    token không ở lại trong lịch sử trình duyệt.
  - Gọi `POST /v1/guardian/session`, thành công thì chuyển `/incidents`.
  - Có `noindex`, `Referrer-Policy: no-referrer`; lỗi thì có hướng dẫn "Nhắn 4 cho bot HỏiCon để nhận liên kết mới".
  - Trang `/login` (không token) chỉ hướng dẫn cách lấy liên kết.
- **(FR-006)** Trang `/incidents`:
  - Hai nhóm "Đang cần chú ý" (`detected`, `assessing`, `awaiting_guardian`, `verifying`, `rescore`, `case_open`) và
    "Đã xong" (`resolved_*`, `closed`).
  - Mỗi thẻ có: mức rủi ro (token `risk.*` + biểu tượng + chữ), trạng thái bằng tiếng Việt, thời điểm tương đối,
    bí danh người cao tuổi, nhãn `[DIỄN TẬP]` (token `drill.*`).
  - Có các trạng thái rỗng, đang tải và lỗi; nút "Tải thêm".
- **(FR-007)** Trang `/incidents/[id]`:
  - Tiêu đề có mức rủi ro, trạng thái và nhãn diễn tập; câu công khai "Đây là trợ lý AI HỏiCon…" ở đầu nội dung do máy
    sinh.
  - Dòng thời gian `transitions` (tác nhân + thời điểm, không có ghi chú tự do).
  - Khung "Trợ lý AI đang làm gì": nạp `/v1/runs/{run_id}/steps` rồi mở luồng (FR-008). Mỗi bước hiện bằng câu tiếng Việt
    dịch từ `node` + `output` theo bảng cố định (plan §5); khóa lạ thì hiện "Bước khác". Không bao giờ in JSON thô.
  - Hành động (chỉ khi sự cố ở `GUARDIAN_DECIDABLE`):
    - "Đã gọi — người thân an toàn" (`safe`), "Nghi lừa đảo" (`emergency_pause` ⇒ `case_open`), "HỏiCon báo nhầm"
      (`false_alarm`), mỗi nút có bước xác nhận thứ hai;
    - "Gọi điện cho người thân" là `tel:` không kèm số.

    Kết quả 409 ⇒ "Sự cố đã được xử lý ở nơi khác", rồi tải lại.
- **(FR-008)** Client luồng trace `useRunStream(runId)`:
  - Mặc định dùng `EventSource` cùng nguồn (cookie tự gửi, tự nối lại theo `retry`, tự gửi `Last-Event-ID`).
  - Nếu bước kiểm ở T004 cho thấy rewrite của Next đệm luồng, dùng phương án dự phòng: route handler **tĩnh**
    `app/v1/web-stream/route.ts` (gọi `/v1/web-stream?run=<run_id>`) chuyển tiếp luồng (đọc cookie, gắn Bearer, trả
    `ReadableStream` không nén). Route phải nằm dưới `/v1` để nhận cookie `Path=/v1`, và phải là route tĩnh: theo tài liệu
    Next 16, rewrite dạng mảng chạy sau route tĩnh nhưng **trước** route động, nên `/v1/…/[id]` sẽ bị rewrite che mất.
  - Bỏ trùng theo `id`; dừng khi nhận `done`; nhận `event: error` hoặc mất kết nối thì hiện "Đang kết nối lại…".
  - Đóng luồng khi rời trang hoặc tab ẩn quá 5 phút.
- **(FR-009)** Kiểm thử:
  - pytest: liên kết đăng nhập, phiên, CSRF, ma trận cô lập, danh sách/chi tiết.
  - Playwright (`apps/web/e2e/`): chặn mạng bằng fixture hợp đồng cho mọi trang, kèm luồng SSE giả; thêm một kịch bản
    đầu–cuối chạy tay với API thật (`HOICON_E2E_LIVE=1`).
  - axe-core, 3 kích thước màn hình, cỡ chữ 200%.
- **(FR-010)** Tài liệu & nghiệm thu:
  - Cập nhật `docs/API.md` (các route guardian, cookie, CSRF), `docs/DESIGN-SYSTEM.md` (trang web người giám hộ) và
    `README` của web (cách chạy e2e).
  - Sinh lại client TS.
  - `evidence.md` có số thật.
  - ROADMAP `P2-12`: chuyển ☑ khi đủ 6 SC.

## 5. Bất biến & ranh giới

1. **ADR-006:** web không bao giờ nhận hay hiện số điện thoại, Zalo ID, `h1`, HMAC, ghi chú tự do. Chi tiết sự cố chỉ
   hiện `last3` nếu API đã cho phép (hiện không trả).
2. **Luật 6 công khai AI:** mọi khối nội dung do máy sinh trên web mở đầu bằng câu công khai. Tin Zalo chứa liên kết đăng
   nhập đi qua `deliver` (đã từ chối tin thiếu câu công khai).
3. **Luật 8 diễn tập:** nhãn `[DIỄN TẬP]` + màu `drill.*` trên thẻ và trang chi tiết; sự cố diễn tập không bao giờ hiện
   như thật.
4. **Luật 11:** mọi quyết định đi qua `apply_guardian_decision` → `IncidentService` (không route mới ghi thẳng
   `incidents.state`).
5. Không thêm migration (scope `guardian_view` đã có). Không đổi hành vi route thiết bị. Không dùng `localStorage` hay
   `sessionStorage` cho token.
6. Thư viện mới chỉ ở `devDependencies`: `@playwright/test`, `@axe-core/playwright` (lý do: luật 16 đòi ảnh chụp web,
   luật 15 đòi kiểm khả năng tiếp cận). Không thêm thư viện runtime.

## 6. Ngoài phạm vi

Dashboard gia đình ngoài danh sách sự cố (danh sách cắt), `/trace` đồ họa xyflow (033), hồ sơ vụ việc (031), quản lý
thành viên, nhiều gia đình trên một tài khoản, đăng nhập bằng email/mật khẩu, thông báo đẩy trên web.
