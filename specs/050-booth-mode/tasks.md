# Tasks: 050 — Chế độ gian trưng bày

**Chế độ chạy**: tự hành một mạch, **bắt đầu sau 09/01/2027** (sau nộp Vòng 2; trước đó không làm — MASTER-PLAN §5 "Wave 5").
`[B-api]` = `backend/**`; `[B-web]` = `apps/web/**`; `[A]` = `apps/android/**`, `scripts/`. Test đỏ trước. `$PYTEST` =
`uv run --directory backend pytest`; `$WEB` = `pnpm --dir apps/web`. **Dừng** khi Verify đỏ 2 lần liên tiếp.

- [ ] T001 [AB] [FR-001] *(kiến trúc sư, checkout chính)* `docs/schemas/booth_session.v1.json`, `booth_event.v1.json` + fixture
  valid/invalid. · Verify: `$PYTEST tests/contract -q`
- [ ] T002 [B-api] [FR-001, FR-002] Test hợp đồng + cổng `HOICON_BOOTH_ENABLED` (404 khi tắt, chỉ gia đình demo, `compose.prod.yml`
  không đặt). · Verify: `$PYTEST tests/contract tests/integration/test_api_booth.py -q`
- [ ] T003 [B-api] [FR-003] Migration `booth_sessions` + `POST /v1/booth/sessions`, `/reset` (xóa sự cố/thiết bị `sim:` của lượt);
  test reset < 60 s, mã đúng bảng chữ D4, hết hạn 15 phút. · Verify: `$PYTEST tests/integration/test_api_booth.py tests/integration/test_schema_*.py -q`
- [ ] T004 [B-api] [FR-004] SSE `GET /v1/booth/join/{code}/stream` (D2), giới hạn kết nối/tần suất, 0 PII; đo 100 kết nối đồng thời.
  · Verify: `$PYTEST tests/integration/test_booth_stream.py -q` (SC-005, SC-006)
- [ ] T005 [B-api] [FR-005] Chế độ gian cho máy `demo` thật: sự cố của thiết bị gia đình demo gắn chế độ gian mang `sim` (không Zalo
  thật). · Verify: `$PYTEST tests/integration/test_api_booth.py -q -k real_device`
- [ ] T006 [B-web] [FR-006] `/demo/console` + `/booth` + `/join/[code]` (token `sim.*` của 033 T022, `title_vi`); Playwright 3 ngữ cảnh
  trình duyệt: tin tới khách < 5 s, reset, mã cũ ⇒ thông báo; axe; ảnh 1920 + 390. Phụ thuộc T002–T004.
  · Verify: `$WEB typecheck && $WEB lint && $WEB e2e booth a11y` (SC-001, SC-002)
- [ ] T007 [A] [FR-007] `scripts/booth-record.py` ghi một lượt replay thật thành `apps/web/public/booth/replay/<kịch bản>.json` (quét PII
  trước khi ghi) + test. · Verify: `python3 -m unittest discover -s scripts/tests`
- [ ] T008 [B-web] [FR-007] `/booth` phát lại cục bộ khi API không trả lời. Playwright chặn mạng ⇒ đủ bước. · Verify: `$WEB e2e booth` (SC-004)
- [ ] T009 [AB] [FR-008] `docs/setup/BOOTH.md` + kịch bản tổng duyệt; `ux-elder-reviewer` (`/join`), `security-privacy-reviewer`.
  · Verify: báo cáo reviewer 0 Chặn/High
- [ ] T010 [AB] [FR-001..FR-008] Cổng + `evidence.md` (SC-003 BLOCKED nếu chưa có máy thật) + dòng P4-02 ROADMAP.
  · Verify: `$PYTEST -q`; `$WEB e2e`; `python3 scripts/check-spec-trace.py`

Thứ tự: T001 → T002 → T003 → T004 → (T005 ‖ T007) → T006 → T008 → T009 → T010.
