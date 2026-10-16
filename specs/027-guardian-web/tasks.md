# Công việc Spec 027: Web người giám hộ

Chạy một mạch, trong một worktree làn B (`../hoicon-wt/server`, nhánh `feat/027-guardian-web`). Mỗi task chạy dòng
`Verify` thấy xanh rồi mới sang task kế tiếp. Lệnh chạy từ gốc repo, với
`PYTEST = uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache`.

## Giai đoạn 1: Hợp đồng
- [ ] T001 [FR-001] Viết `docs/schemas/guardian_session.v1.json` và `incident_list.v1.json`; thêm `$defs/summary` vào
  `incident.v1.json` nếu chưa có, giữ tương thích ngược. Viết fixture `valid`/`invalid`. Fixture invalid phải có:
  - token chứa ký tự lạ;
  - phản hồi phiên có trường `token` hoặc `phone`;
  - `next_cursor` quá dài.

  · Verify: `$PYTEST tests/contract/test_guardian_schemas.py`
- [ ] T002 [FR-001] Viết `backend/tests/contract/test_guardian_schemas.py`: valid qua, invalid trượt, và các fixture cũ
  của `incident.v1` vẫn qua.
  · Verify: như T001

## Giai đoạn 2: Kiểm rủi ro
- [ ] T003 [FR-008] Đọc `node_modules/next/dist/docs` phần `rewrites`, `compress` và streaming của route handler
  (`apps/web/AGENTS.md` bắt buộc). Ghi kết luận ngắn vào `evidence.md`.
  · Verify: evidence có mục "Next 16 và SSE"
- [ ] T004 [FR-008] Đo rewrite với SSE thật:
  - chạy API (`uvicorn`, cổng 18000) có một lượt `running`, và `pnpm --dir apps/web build && pnpm --dir apps/web start`;
  - dùng `curl -N` lấy `http://localhost:3100/v1/runs/<id>/stream` (cookie hoặc Bearer test);
  - chèn một bước rồi đo thời gian tới khi thấy khung.

  Nếu > 1 s, hoặc có `Content-Encoding: gzip`, thì chọn phương án route handler ở plan D2. Ghi số đo và lựa chọn vào
  `evidence.md`.
  · Verify: evidence có số đo và lựa chọn (rewrite hoặc route handler)

## Giai đoạn 3: Máy chủ
- [ ] T005 [FR-003] `api/auth.py`:
  - `get_current_guardian` nhận cookie `hc_guardian` khi không có Bearer;
  - thêm dependency `require_same_origin` cho lệnh ghi xác thực bằng cookie (`Origin` thuộc `settings.web_origins`,
    hoặc `Sec-Fetch-Site: same-origin`; nếu không ⇒ 403);
  - thêm `GUARDIAN_WEB_TTL = 7 ngày`;
  - gắn `require_same_origin` vào `POST /v1/incidents/{id}/decision`.

  · Verify: `$PYTEST tests/integration/test_guardian_session.py tests/integration/test_guardian_alert.py`
- [ ] T006 [FR-002] Lệnh `login` trên Zalo:
  - phân loại "4" / "web" / "đăng nhập" (bỏ dấu, không phân biệt hoa thường) trong `channels/inbound.py`, nơi đang
    phân loại "1/2/3" (thêm loại `login`);
  - `updates.py` xử lý: người đã ghép ⇒ vô hiệu token `guardian_view` cũ chưa dùng, rồi phát token mới hạn 15 phút;
    người chưa ghép ⇒ hướng dẫn ghép đôi;
  - hạn mức 5 lần/giờ đếm trên `action_tokens`;
  - trả lời bằng `texts.guardian_login_link` qua `deliver` với chỗ trống liên kết, theo đúng cơ chế của 023.

  · Verify: `$PYTEST tests/integration/test_guardian_login.py`
- [ ] T007 [FR-002] [FR-009] Viết `backend/tests/integration/test_guardian_login.py` với Zalo mock. Các ca:
  - tin gửi đi mở đầu bằng câu công khai AI và có `/login/`;
  - DB chỉ có SHA-256;
  - `jobs.payload` và `messages_out` không có token thô;
  - liên kết mới vô hiệu liên kết cũ;
  - lần thứ 6 trong giờ thì từ chối nhẹ nhàng;
  - người chưa ghép nhận hướng dẫn;
  - diễn tập không ảnh hưởng.

  · Verify: như T006
- [ ] T008 [FR-003] Viết `backend/src/hoicon/api/routers/guardian.py`:
  - `POST /v1/guardian/session`: khóa dòng token `FOR UPDATE`, kiểm scope `guardian_view` + hạn + chưa dùng, đặt
    `used_at`, đặt cookie; mọi lỗi ⇒ 410 cùng một thông điệp;
  - `GET /v1/guardian/me`;
  - `DELETE /v1/guardian/session`.

  Gắn vào `api/main.py`. Bộ lọc log của 023 phải che cả `/login/<token>` nếu đường dẫn này lọt vào log API.
  · Verify: `$PYTEST tests/integration/test_guardian_session.py`
- [ ] T009 [FR-003] [FR-009] Viết `backend/tests/integration/test_guardian_session.py`. Các ca:
  - đổi token thành công thì có cookie đúng cờ (`HttpOnly`, `SameSite=Strict`, `Path=/v1`, `Secure` khi không phải dev);
  - token dùng lại, quá hạn, sai scope (`incident_decision`) hoặc không tồn tại đều trả 410 với cùng thân;
  - hai request đồng thời cùng token thì chỉ một thành công;
  - `me`, đăng xuất;
  - thành viên bị xóa thì 401;
  - lệnh ghi bằng cookie mà thiếu `Origin` thì 403, có `Origin` đúng thì qua;
  - Bearer vẫn chạy như cũ;
  - `caplog` không có token.

  · Verify: như T008
- [ ] T010 [FR-004] Thêm `GET /v1/guardian/incidents` (khóa `(opened_at, id)`, `status=open|closed`, 20 sự cố/trang, đang
  mở trước) và `GET /v1/guardian/incidents/{id}` (`IncidentDetail` + `elder_alias` + `run_id`). Tách `_load_incident`
  trong `incidents.py` để dùng chung, giữ nguyên hành vi route thiết bị.
  · Verify: `$PYTEST tests/integration/test_guardian_incidents.py tests/integration/test_api_incidents.py`
- [ ] T011 [FR-004] [FR-009] Viết `backend/tests/integration/test_guardian_incidents.py`:
  - ma trận cô lập: 2 gia đình × mọi route mới và `/v1/runs/*`, `/v1/incidents/{id}/decision`; nhà khác ⇒ 404;
  - phân trang không trùng, không sót;
  - nhóm mở/đóng đúng tập trạng thái;
  - sự cố diễn tập có `is_drill`;
  - phản hồi khớp `incident_list.v1`.

  · Verify: như T010
- [ ] T012 [FR-010] Sinh lại client TS. Cập nhật `docs/API.md` cho các route guardian, cookie, CSRF và lệnh "4" trên Zalo.
  · Verify: `bash scripts/gen-api-client.sh && pnpm --dir apps/web typecheck`

## Giai đoạn 4: Web
- [ ] T013 [FR-005] Viết `apps/web/src/app/login/page.tsx` (hướng dẫn) và `login/[token]/page.tsx`:
  - `replaceState('/login')` trước khi `fetch`;
  - đặt `noindex` và `Referrer-Policy: no-referrer` ở layout;
  - có trạng thái đang đổi phiên, lỗi 410 kèm hướng dẫn, thành công thì chuyển `/incidents`.

  · Verify: `pnpm --dir apps/web lint && pnpm --dir apps/web typecheck`
- [ ] T014 [FR-006] Viết `apps/web/src/app/incidents/page.tsx`:
  - hai nhóm, thẻ mức rủi ro (token `risk.*` + biểu tượng + chữ), nhãn `[DIỄN TẬP]` (token `drill.*`);
  - có trạng thái rỗng, đang tải và lỗi, nút "Tải thêm";
  - 401 thì chuyển `/login`.

  · Verify: như T013
- [ ] T015 [FR-007] [FR-008] Viết `apps/web/src/app/incidents/[id]/page.tsx`, `src/lib/stream.ts` (`useRunStream`) và
  `src/lib/steps.ts` (bảng dịch ở plan §5):
  - dòng thời gian chuyển trạng thái;
  - khung trace có câu công khai AI;
  - 3 nút quyết định có bước xác nhận, cộng `tel:` không kèm số;
  - 409 ⇒ thông báo rồi tải lại;
  - phương án luồng theo kết luận T004.

  · Verify: `pnpm --dir apps/web lint && pnpm --dir apps/web typecheck && pnpm --dir apps/web build`

## Giai đoạn 5: Kiểm thử web
- [ ] T016 [FR-009] Thêm `@playwright/test` và `@axe-core/playwright` vào `devDependencies` (lý do ghi trong commit),
  `playwright.config.ts` (Chromium, `webServer: next start`), script `e2e`, và `apps/web/e2e/fixtures.ts` chặn `/v1/*`
  bằng fixture trong `docs/schemas/fixtures/`, kèm luồng SSE giả.
  · Verify: `pnpm --dir apps/web exec playwright install chromium && pnpm --dir apps/web e2e --list`
- [ ] T017 [FR-009] Viết `e2e/login.spec.ts`, `e2e/incidents.spec.ts`, `e2e/detail.spec.ts`. Các ca:
  - URL không còn token sau khi đăng nhập;
  - lỗi 410;
  - danh sách hai nhóm và nhãn diễn tập;
  - chi tiết nhận bước từ luồng giả, bỏ trùng theo `id`, dừng khi nhận `done`;
  - mất kết nối thì hiện "Đang kết nối lại…";
  - quyết định có bước xác nhận;
  - xử lý 409;
  - node lạ ⇒ "Bước khác".

  · Verify: `pnpm --dir apps/web e2e`
- [ ] T018 [FR-009] Viết `e2e/a11y.spec.ts`:
  - axe 0 vi phạm `serious`/`critical` trên 4 trang;
  - chụp ảnh ở 360 / 768 / 1280 px và cỡ chữ 200% (CSS `html { font-size: 200% }`), lưu
    `~/hoicon-evidence/027-guardian-web/`;
  - kiểm không tràn ngang bằng `scrollWidth <= clientWidth`.

  · Verify: `pnpm --dir apps/web e2e a11y`
- [ ] T019 [FR-009] Viết `e2e/live.spec.ts` (chỉ chạy khi `HOICON_E2E_LIVE=1`):
  - dùng API + DB dev thật; lấy token bằng lệnh ops mới `python -m hoicon.ops.guardian_link --member <id>` (in liên kết
    ra màn hình; chặn chạy khi `HOICON_ENV=prod`);
  - đăng nhập → danh sách → chi tiết;
  - chèn bước vào `agent_steps`, đo thời gian hiện (SC-004);
  - quyết định → sự cố chuyển trạng thái.

  · Verify: `HOICON_E2E_LIVE=1 pnpm --dir apps/web e2e live` (máy dev, API và DB đang chạy)
- [ ] T020 [FR-009] Thêm bước `pnpm e2e` (bỏ qua `live`) vào `.github/workflows/web.yml`.
  · Verify: `grep -n "e2e" .github/workflows/web.yml`

## Giai đoạn 6: Nghiệm thu
- [ ] T021 [FR-010] Chạy đủ bộ lệnh kiểm:
  - `$PYTEST`;
  - `ruff check` và `ruff format --check` (`--cache-dir /tmp/ruff_cache src/ tests/`);
  - `pnpm --dir apps/web lint typecheck build e2e`;
  - gitleaks **từng thư mục**: `backend/src`, `backend/tests`, `apps/web/src`, `apps/web/e2e`, `docs/schemas`,
    `specs/027-guardian-web`;
  - `python3 scripts/check-spec-trace.py`.

  Gửi ảnh chụp cho `ux-elder-reviewer` (phần câu chữ và độ dễ đọc) và diff phần xác thực cho `security-privacy-reviewer`.
  Sửa hết mục High.
  · Verify: mọi lệnh xanh; báo cáo reviewer không còn High chưa xử lý
- [ ] T022 [FR-010] Cập nhật `docs/DESIGN-SYSTEM.md` (trang web người giám hộ), README của web (cách chạy e2e), và ROADMAP
  "Ghi chú" (chọn shadcn để dành cho 033). Điền `evidence.md` bằng số thật. Đặt ROADMAP `P2-12` ☑ chỉ khi đủ 6 SC.
  · Verify: `python3 scripts/check-spec-trace.py` ⇒ 0 lỗi
