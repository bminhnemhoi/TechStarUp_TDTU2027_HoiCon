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
