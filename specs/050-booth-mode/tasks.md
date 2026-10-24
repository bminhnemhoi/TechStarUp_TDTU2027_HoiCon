# Công việc Spec 050: Chế độ gian trưng bày

> **Đã đối soát 24/10/2026 (kiến trúc sư):** bản của làn B được giữ làm gốc (giai đoạn 1 đã thi công). Giai đoạn 2 (T001, T011–T013) làm sau 09/01/2027 (MASTER-PLAN §5 Wave 6).

## Cách chạy

- **Làn B** (`feat/050-booth-mode`): `[B-web]` = `apps/web/**`, `[B-api]` = `backend/**`. `[A]` để làn A. `[Opus]` = hợp đồng (`docs/schemas`), làn B không làm.
- **Giai đoạn 1 (làm được ngay, chỉ hợp đồng `sim_*` có sẵn):** T002–T010, T014. **Giai đoạn 2 (BLOCKED chờ T001):** T011–T013.
- **Biến dùng trong lệnh**: `PYTEST = uv run --directory backend pytest -o cache_dir=/tmp/pytest_cache`; `WEB = pnpm --dir apps/web`.
  Playwright cần API cổng 18000 + web 3100 chạy với `HOICON_SIM_ENABLED=true` và gia đình demo (`ops guardian_link --seed`), xem `apps/web/e2e/sim.spec.ts`.
- **Dừng**: `Verify` đỏ 2 lần ⇒ dừng task, chẩn đoán (`diagnosing-bugs`); cần đổi `docs/schemas` ⇒ dừng, báo Opus. Không gọi LLM thật (mọi lượt `llm: "replay"`).
- Next.js ở đây khác bản quen thuộc: đọc `apps/web/node_modules/next/dist/docs/` trước khi viết trang (xem `apps/web/AGENTS.md`).

## Giai đoạn 0: Hợp đồng

- [x] T001 [Opus] [FR-001] Viết `docs/schemas/sim_reset.v1.json` (số lượt đã xóa, thời gian, `is_demo`) và `booth_join.v1.json` (đổi mã lấy phiên demo) + fixture
  valid/invalid. **BLOCKED**: ngoài quyền làn B. Gỡ chặn T011–T013.

## Nhóm [B-web] — giai đoạn 1

- [x] T002 [B-web] [FR-002, FR-006] `apps/web/src/lib/booth.ts`: danh sách phát có kiểu (3 kịch bản: `fake_police_safe_account_002`, `fake_bank_card_locked_002`, một ca hợp lệ
  `benign_family_son_rent_002`; câu trả lời của bác và quyết định của con cho từng ca), kiểu bản ghi, hàm kiểm khung theo `sim_run.v1` (thủ công, đóng).
  · Verify: `$WEB typecheck`
- [x] T003 [B-web] [FR-006, SC-005] Ghi 3 bản ghi vào `apps/web/public/booth/replay/{scenario}.json` bằng `e2e/booth-record.spec.ts` (chỉ chạy khi `BOOTH_RECORD=1`; chạy qua
  `/v1/sim/*` của gia đình demo, `llm: "replay"`). Test kiểm: mỗi khung hợp `sim_run.v1`, không có chuỗi giống số điện thoại thô, mọi tin mở đầu "Đây là trợ lý AI HỏiCon".
  · Verify: `BOOTH_RECORD=1 $WEB e2e booth-record` rồi `$WEB e2e booth` (phần kiểm tệp)
- [x] T004 [B-web] [FR-003, FR-006] `apps/web/src/lib/use-booth-runner.ts`: chạy danh sách phát trực tiếp qua `/v1/sim/*`, `ReplayPlayer` từ bản ghi, phát hiện mất mạng (D4:
  `onLine`, 2 lần hỏng/quá 3 s, chọn tay), đo `t_alert_ms` (D5), `BroadcastChannel` giữa `/booth` và console, trả lượt cho console (D7: không lưu gì ở trình duyệt).
  · Verify: `$WEB typecheck && $WEB lint`
- [x] T005 [B-web] [FR-002, FR-008, SC-006] `apps/web/src/components/booth-columns.tsx` + `apps/web/src/app/booth/page.tsx`: 3 cột (điện thoại của bác · trợ lý AI · Zalo của con), chữ ≥ 28 px,
  băng rôn "MÔ PHỎNG — dữ liệu hư cấu" và (khi phát lại) "ĐANG PHÁT LẠI BẢN GHI — không phải trực tiếp"; một cột ở 390 px; "Trang này chưa mở" khi API 404; chuyển hướng đăng nhập khi 401.
  · Verify: `$WEB typecheck && $WEB lint && $WEB build`
- [x] T006 [B-web] [FR-004, FR-005a] `apps/web/src/app/demo/console/page.tsx`: danh sách kịch bản + Bắt đầu, chế độ (Trực tiếp · Bản ghi), Đặt lại màn hình (dừng phát, xóa trạng thái, hiện lệnh
  `python -m hoicon.ops.booth reset`), trạng thái kết nối, bảng lượt gần đây, bộ đếm đạt liên tiếp (3 ⇒ "Đạt Gate G4 ở máy này"), nút "Ghi bản ghi" (tải JSON).
  · Verify: `$WEB typecheck && $WEB lint && $WEB build`
- [x] T007 [B-web] [FR-010, SC-001, SC-002, SC-003, SC-006] Playwright `e2e/booth.spec.ts` + `e2e/booth-offline.spec.ts` (chạy với API thật ở `llm: "replay"`): (a) một lượt hoàn chỉnh ≤ 90 s; (b) 3 lượt liên
  tiếp có `t_alert_ms` < 5000 (ghi bảng); (c) chặn mạng giữa lượt ⇒ băng rôn "BẢN GHI" ≤ 6 s và đủ 3 cột, có mạng ⇒ lượt kế trực tiếp; (d) ảnh 390/768/1440 px, axe 0 lỗi; (e) chữ chính ≥ 28 px.
  · Verify: `$WEB e2e booth booth-offline`
- [x] T008 [B-web] [FR-002] `ux-elder-reviewer` đọc ảnh `/booth` và `/demo/console` (chữ, thứ tự, hoảng sợ, băng rôn); sửa hết Chặn/Cao/Trung bình.
  · Verify: báo cáo ghi vào `evidence.md`

## Nhóm [B-api] — giai đoạn 1

- [x] T009 [B-api] [FR-005b, SC-004] `backend/src/hoicon/ops/booth.py` (`reset`): chỉ gia đình `is_demo` và `HOICON_ENV=dev`/cờ tường minh `--confirm-demo`; xóa sự cố mô phỏng (thiết bị nhãn `sim:`) + `agent_runs` + `agent_steps` + job + checkpoint
  của các sự cố đó; in số đã xóa và thời gian; lũy đẳng. Test `backend/tests/integration/test_ops_booth.py`: không đụng gia đình thật, không đụng sự cố demo thường (không `sim`), lần hai xóa 0, thời gian < 30 s với 20 lượt.
  · Verify: `$PYTEST tests/integration/test_ops_booth.py` và đo thời gian ghi vào `evidence.md`
- [x] T010 [B-api] [FR-008] Kiểm cổng: `HOICON_SIM_ENABLED=false` ⇒ `/booth` hiện "chưa mở" (404 từ API, đã phủ ở 033) và `compose.prod.yml` không bật cổng (test hạ tầng có sẵn). Thêm kiểm: ảnh container prod **không** chứa `public/booth/replay` nào có
  số điện thoại thô (quét tệp). 
  · Verify: `python3 -m unittest discover -s scripts/tests -p test_deploy_vps.py` và `$PYTEST tests/unit/test_booth_recordings.py`

## Giai đoạn 2 — BLOCKED bởi T001

- [x] T011 [B-api] [FR-005c] `POST /v1/sim/reset` (cùng `ops.booth.reset`), gắn nút Đặt lại của console. **BLOCKED**: cần `sim_reset.v1`.
- [x] T012 [B-api] [FR-007] Mã tham gia (≤ 10 phút, ≤ 50 khách/mã, vô hiệu khi đặt lại) + `POST /v1/booth/join` đổi mã lấy phiên demo. **BLOCKED**: cần `booth_join.v1`.
- [x] T013 [B-web] [FR-007] Trang `/join/[code]` (chữ lớn, "bản trình diễn — dữ liệu hư cấu", xem + quyết định) và nút tạo mã/QR ở console. **BLOCKED**: sau T012.

## Nhóm [A]

- [x] T014 [A] [FR-009] `:demobank` + kịch bản máy ảo tại gian: `emu-scenario` gọi theo tên danh sách phát, tài liệu bấm máy trong `docs/EMULATOR.md`. Làn A; không làm ở đây.

## Hoàn tất

- [x] T015 [B] Bộ kiểm đầy đủ (`$PYTEST`, ruff, eval smoke/full, spec-trace, gitleaks từng thư mục, `alembic heads` = 1, `$WEB typecheck` + e2e) và điền `evidence.md` (SC-001…SC-006; SC nào chưa đo ghi rõ lý do).
  · Verify: lệnh thoát 0; `python3 scripts/check-spec-trace.py`

## Đối soát kiến trúc sư 24/10/2026

- T001 **xong 24/10/2026** (nhà điều phối, Tiến cho làm hết việc thực thi được): `sim_reset.v1.json`, `booth_join.v1.json` + fixture. Giai đoạn 2 (T011–T013) gỡ chặn. Làn B thêm test hợp đồng vào `tests/contract/test_sim_schemas.py` ở T011.
- [x] T016 [B-web] [FR-002, FR-004] Sửa các mục Medium còn lại của `ux-elder-reviewer` (evidence 050): bỏ thuật ngữ nội bộ ở console ("Gate G4", "replay" ⇒
  "Bản ghi"), băng rôn diễn tập dùng màu diễn tập riêng (DESIGN-SYSTEM, luật 15). `?fast=1` chỉ có hiệu lực khi `NODE_ENV !== "production"`.
  · Verify: `pnpm --dir apps/web typecheck && pnpm --dir apps/web e2e booth` + ảnh 390/1440 reviewer đọc lại ⇒ 0 Medium

## Lượt 9 (nhà điều phối 24/10/2026)
- Quyết định QR (T013): **chưa thêm thư viện** (luật 14) — console hiện mã 6 ký tự cỡ lớn + địa chỉ ngắn để khách gõ; ghi ROADMAP "Ghi chú" nếu BGK cần quét.
- [ ] T017 [B] [FR-007, FR-008] Medium bảo mật còn lại của T013 (evidence 050): #4 làm đầy độ dài mã/so sánh hằng thời gian, #5 hạn mức SSE
  của phiên khách tách khỏi người giám hộ, #7 Caddyfile che `/join/<mã>` trong log, #8 khóa HMAC mã tham gia lấy từ khóa riêng (không dùng
  pepper số điện thoại), #9 `/join` khi cổng tắt ⇒ "Trang này chưa mở". Mỗi mục test đỏ trước. · Verify: `$PYTEST tests/integration -q -k "booth or join"` + `$WEB e2e booth join`
