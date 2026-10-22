# Bằng chứng nghiệm thu Spec 033: Web `/sim`, `/trace`, `/eval`

- **Trạng thái (18/10/2026)**: chỉ có spec/plan/tasks và hợp đồng (T001). **Chưa code.**
- **Nguồn số dự kiến**: máy dev (API 18000 + web 3100, Playwright Chromium), chế độ `replay`. Không có số máy thật hay VPS.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 toàn luồng trên web | ≤ 5 thao tác, bước hiện ≤ 1 s | Playwright | chưa chạy | CHƯA ĐO |
| SC-002 tất định | hai lượt replay giống nhau | Playwright | chưa chạy | CHƯA ĐO |
| SC-003 cô lập | cổng, chỉ demo, Zalo mock ép, hạn mức | pytest | chưa chạy | CHƯA ĐO |
| SC-004 tiếp cận | axe 0 lỗi; bản chữ trace đủ bước | Playwright + axe | chưa chạy | CHƯA ĐO |
| SC-005 đúng đồ thị | topology = đồ thị biên dịch | pytest | chưa chạy | CHƯA ĐO |
| SC-006 không PII | 0 số/h1/tên gói trong API + DOM | pytest + Playwright | chưa chạy | CHƯA ĐO |
| SC-007 video | một lượt quay dùng được | đội quay | — | BLOCKED (P2-21) |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| jsonschema + `referencing`: fixture 4 lược đồ (8 valid, 15 invalid) | valid hợp lệ, invalid bị từ chối |
| `uv run --directory backend pytest -q tests/contract` | 257 passed (lược đồ mới chưa có test riêng — T002) |

## Wave 3 — [B-api] T002–T009, T011 (làn B, 22/10/2026)

- **T002–T009 ĐẠT:** `tests/contract/test_sim_schemas.py` (9), `tests/integration/test_api_sim.py` (22), `test_api_graphs.py` (5). Cổng tắt ⇒ 404 cả khi chưa đăng nhập; gia đình thật ⇒ 404; thiếu phiên ⇒ 401; sai `Origin` ⇒ 403; `compose.prod.yml` không đặt cổng; 0 lời gọi tới client Zalo với `ZALO_MODE=live`; một lượt `replay` của `fake_police_safe_account_002` có dãy `agent_steps.node` và mức **bằng lượt eval cùng ca**; hạn mức 10/giờ và 3 đồng thời ⇒ 429 + `Retry-After`; runtime hết hạn ⇒ `fallback`.
- **T011 ĐẠT:** `scripts/gen-api-client.sh` sinh lại `schema.d.ts`; `pnpm --dir apps/web typecheck` xanh; `docs/API.md`, `docs/AGENTS.md`, `docs/setup/SIM.md` cập nhật.
- **Lệch so với chữ của task (quyết định kỹ thuật, cần Opus cân nhắc sửa plan):**
  1. Mỗi lượt `POST /runs` tạo MỘT thiết bị demo riêng (nhãn `sim:<kịch bản>`, cũng là dấu "sự cố mô phỏng" bền, không cần migration) thay vì một thiết bị dùng chung, vì dùng chung thì `correlate_event` gom hai kịch bản chạy cùng lúc vào một sự cố. Vì vậy `ops guardian_link --seed` KHÔNG tạo thêm thiết bị (T003).
  2. "Bộ ghi mock" của tin người giám hộ là chính `jobs.payload` (đã che PII, `sim: true`); `send_to_guardian` trả `"simulated"` trước khi chạm `messages_out` hay client Zalo.
  3. Đồ thị lượt mô phỏng khởi động tại chỗ bằng runtime phát lại (`ingest_events(defer_graph=True)` rồi `start_prepared(sim=True)`), không qua job `start_graph`; sự kiện nhận id mới mỗi lượt (`build_event` cho id tất định theo kịch bản nên chạy lại sẽ trùng).
  4. `pending_question.expires_at` lấy từ hẹn giờ `ask_elder`, thiếu ⇒ +60 giây.
- **Ngoài quyền:** dòng ROADMAP của 033 (cấm sửa ROADMAP).

## Wave 3 — [B-web] T012–T015 (làn B, 22/10/2026)

- **T012 ĐẠT:** `@xyflow/react@12.12.0` (MIT, ghim đúng phiên bản; lý do ở plan D6) chỉ nạp động (`next/dynamic`, `ssr: false`) ở `/sim` và `/trace`. Kích thước JS gzip trước/sau: tổng chunk 202.572 B → 283.994 B (xyflow nằm trong chunk riêng của hai trang mới); trang `/incidents` **không đổi** 11.899 B (đo bằng client-reference-manifest sau `pnpm build`).
- **T013 ĐẠT:** `/trace/[runId]` = sơ đồ (bố cục tĩnh dọc từ `graph_topology`) + bản chữ + chi tiết khối; trạng thái nút bằng màu token + biểu tượng + chữ; lượt nhà khác/404 ⇒ "Không tìm thấy"; link "Xem sơ đồ các bước" ở trang chi tiết sự cố. `e2e/trace.spec.ts` (8 test): đủ bước, chọn khối, bước SSE mới < 1 s, 404, sơ đồ lỗi vẫn có bản chữ, axe + ảnh 390/768/1440.
- **T014 ĐẠT:** `/sim` đủ 3 cột (≥ 1024 px) / 3 thẻ có tab (< 1024 px), nhãn "MÔ PHỎNG", nhãn "kịch bản nháp", nút E8 ≥ 64 px, quyết định có xác nhận (dùng lại câu chữ 027 qua `lib/decision-copy.ts`), API 404 ⇒ "Trang này chưa mở". `e2e/sim.spec.ts` (10 test): (a) lừa đảo từ Bắt đầu tới "nghi lừa đảo" trong 4 thao tác, tin mở đầu công khai AI; (b) ca hợp lệ ⇒ `note`; (c) chạy hai lần cho cùng bước + chữ tin; (d) DOM không có số điện thoại/h1/tên gói; 404/429; axe + ảnh 390/768/1440. **Giới hạn trung thực:** e2e dùng fixture hợp đồng chặn mạng (như 027), nên (c) chứng minh giao diện, còn tính tất định của bước nằm ở `test_api_sim.py` (lượt replay = lượt eval); chưa chạy e2e với API thật.
- **T015 ĐẠT:** `/sim` và `/trace` thêm vào `e2e/a11y.spec.ts` (360/768/1280 + chữ 200%); `gen-design-tokens.py --check` exit 0; không mã màu cứng ngoài nét cạnh sơ đồ (`#1f3a5f` = token brand-navy, vì React Flow nhận giá trị chứ không nhận lớp Tailwind).
- Toàn bộ e2e web: **86 passed, 1 skipped (live)**; `pnpm typecheck`, `lint`, `build` xanh. Ảnh: `~/hoicon-evidence/033-sim-trace/{sim,trace}-{390,768,1440}.png`.
- **`ux-elder-reviewer` (T013/T014):** 0 Chặn, 4 Cao đều SỬA (chữ sơ đồ quá nhỏ ⇒ khoảng cách hàng + chiều cao theo số hàng + không thu nhỏ; "gặp lỗi" mâu thuẫn bản chữ khi có `fallback_used`; lưới 3 cột bắt đầu từ 1024 px thay vì 768 px; canvas bắt thao tác chạm ⇒ tắt kéo/thu phóng). Trung bình đã sửa: chú thích ký hiệu `aria-hidden` + bỏ tiếng Anh khỏi dòng chính, tiêu đề + vùng đọc bước mới cho danh sách, bước không có khối không còn là nút, khối "Kết thúc" theo trạng thái lượt, nút trả lời `text-title`, "Nghe lại câu hỏi" (đọc to), trạng thái rỗng sau khi bác trả lời, nhãn chế độ chạy dễ hiểu, thông báo 404 bớt kỹ thuật, báo mất kết nối khi thăm dò, banner dính + biểu tượng, "(mô phỏng)" ở cột AI. **Chưa sửa, cần Opus/hợp đồng:** tên kịch bản tiếng Việt trong ô chọn (cần `title_vi` trong `sim_scenarios.v1`), banner dùng màu diễn tập (cần token màu riêng cho mô phỏng), `/trace` mở từ lượt mô phỏng chưa có nhãn (cần cờ `is_sim` trong hợp đồng), đồng bộ giờ tin Zalo mock với giờ bước, chữ hoa đầu `describeStep`, mẫu tab đủ phím mũi tên.
