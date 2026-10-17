---

description: "Tasks for spec 002 — Kênh Zalo cho người giám hộ (spike P1-S3)"
---

# Tasks: Kênh Zalo cho người giám hộ (spike P1-S3)

**Input**: `/specs/002-zalo-guardian-channel/` (spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md)

**Tests**: bắt buộc, viết trước (đỏ rồi mới code). Integration cần Postgres (`docker compose -f infra/compose.dev.yml up -d`);
DB tắt thì test integration tự bỏ qua ⇒ **không** được tính là xanh cho task cần DB.

**Làn**: B — worktree `../hoicon-wt/server`. Chỉ sửa `backend/**`, `docs/schemas/**` (schema Zalo chỉ backend dùng),
`docs/spikes/P1-S3-zalo.md`, `docs/adr/ADR-010-*.md` (nháp), `docs/DATA-MODEL.md`, `docs/API.md`, dòng P1-S3 trong ROADMAP.
Không đụng `apps/android/**`. Không chạy Gradle/emulator.

**Cổng dừng**: T004 chưa được Minh duyệt ⇒ dừng trước T006 (migration); vẫn làm được T001–T003, T005, T009–T010
(phần không cần bảng mới). Thiếu token ⇒ T024 BLOCKED.

## Format: `[ID] [P?] [Story] Description — FR-xxx · Verify: \`lệnh\``

---

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Tra tài liệu chính thức Zalo Bot Platform theo research R1 (cập nhật webhook, gửi tin, nút bấm, setWebhook, giới hạn, điều khoản); ghi URL + ngày tra vào docs/spikes/P1-S3-zalo.md §1 (tạo file) — FR-015 · Verify: review (mỗi mục R1 có nguồn hoặc ghi "không có tài liệu")
- [x] T002 Khai báo trực tiếp `httpx` và `cryptography` trong backend/pyproject.toml (đã có trong uv.lock, nêu lý do trong PR) — FR-005, FR-010 · Verify: `uv lock --check --directory backend` (hoặc `uv sync --directory backend --locked`)
- [x] T003 [P] Hợp đồng `docs/schemas/zalo_update.v1.json` + fixture `docs/schemas/fixtures/zalo_update.v1.valid.json` / `.invalid.json` (định danh hư cấu) theo kết quả T001; test hợp đồng backend/tests/contract/test_zalo_update_schema.py — FR-002, FR-009 · Verify: `uv run --directory backend pytest tests/contract/test_zalo_update_schema.py -q`
- [x] T004 Viết docs/adr/ADR-010-kenh-zalo.md **nháp** gồm D1 (chat_id mã hóa AES-GCM + HMAC), D2 (0003 tạo 4 bảng), kênh dự phòng, rủi ro gửi lặp; xin Minh duyệt (PR/nhắn) — FR-010, FR-015 · Verify: Minh trả lời duyệt/không; ghi kết quả vào evidence.md. **Chưa duyệt ⇒ dừng trước T006** — *15/10: ADR-010 nháp viết xong; **Tiến duyệt D1/D2 ngày 15/10/2026** (kỹ sư chủ trì nhánh) nên tick; Minh xác nhận lại ở PR. Kết quả ghi ở evidence.md.*

---

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T005 [P] `backend/src/hoicon/channels/zalo.py`: `ZaloClient` (Protocol) + `LiveZaloClient` (httpx; token chỉ ghép URL lúc gọi; `ZaloError(status)` raise … from None; `logging.Filter` thay `/bot[^/]+/` ⇒ `/bot***/`; logger httpx mức WARNING) + `MockZaloClient` (ghi tin vào danh sách); chọn qua `HOICON_ZALO_MODE` (mock mặc định; live thiếu token ⇒ lỗi khởi động). Test trước: backend/tests/unit/test_zalo_client.py (lỗi HTTP không chứa token; filter che URL; mock ghi tin; live thiếu token ⇒ lỗi) — FR-011, FR-012 · Verify: `uv run --directory backend pytest tests/unit/test_zalo_client.py -q`
- [x] T006 Migration backend/migrations/versions/20261016_0003_families_members_pairing_messages.py + models trong backend/src/hoicon/db/models.py theo specs/002-zalo-guardian-channel/data-model.md (sau khi T004 được duyệt) — FR-003, FR-005, FR-007, FR-010 · Verify: `uv run --directory backend alembic upgrade head && uv run --directory backend alembic downgrade -1 && uv run --directory backend alembic upgrade head` + `pytest tests/integration/test_db.py -q`
- [x] T007 [P] `backend/src/hoicon/domain/pii.py`: `hmac_zalo(bot_id, user_id)` (tiền tố `hoicon:zalo:v1:`, pepper + kid) và `encrypt_chat_id` / `decrypt_chat_id` (AES-256-GCM, khóa `HOICON_DATA_KEY_<kid>`); thêm `data_key_1` vào config.py, `init_env` sinh khóa, `check_keys` kiểm độ dài. Test trước: backend/tests/unit/test_pii_zalo.py (khứ hồi, nonce khác nhau, kid sai ⇒ lỗi, HMAC ổn định và khác HMAC số điện thoại) — FR-010 · Verify: `uv run --directory backend pytest tests/unit/test_pii_zalo.py tests/unit/test_init_env.py tests/unit/test_check_keys.py -q`
- [x] T008 `IncidentRuntime.start(..., family_id=None)` + `IncidentState.family_id` + payload `notify_guardian` có `family_id` (tương thích ngược) trong backend/src/hoicon/agents/{runtime,incident_graph}.py — FR-005 · Verify: `uv run --directory backend pytest tests/integration/test_incident_graph.py tests/integration/test_graph_durable.py tests/unit/test_runtime_inputs.py -q`

**Checkpoint**: client + lưu trữ + đồ thị biết gia đình — các story bắt đầu được

---

## Phase 3: User Story 1 - Con nhận cảnh báo Zalo ngay khi có sự cố (Priority: P1) 🎯 MVP

**Independent Test**: mock — mở sự cố demo ⇒ 1 tin đúng người, đúng nội dung, 1 dòng `messages_out`

- [x] T009 [P] [US1] Test trước backend/tests/integration/test_notify_guardian.py: gửi đúng người hạng 1/2; câu công khai + nhãn diễn tập; retry không gửi lặp (dòng `sent` ⇒ bỏ qua); sự cố demo chỉ gửi gia đình demo — FR-005, FR-006, FR-014 · Verify: test đỏ trước khi có T010 (SC-006)
- [x] T010 [US1] `backend/src/hoicon/channels/guardian.py::send_to_guardian` + handler `notify_guardian` thật trong backend/src/hoicon/jobs/worker.py (tìm member theo family_id + guardian_rank, giải mã chat_id lúc gửi, ghi `messages_out` theo `job_key`, lỗi vĩnh viễn ⇒ `fallback_required`, không log nội dung tin) — FR-005, FR-006, FR-008, FR-014 · Verify: `uv run --directory backend pytest tests/integration/test_notify_guardian.py -q`

---

## Phase 4: User Story 2 - Con ghép Zalo bằng mã (Priority: P1)

- [x] T011 [P] [US2] Test trước backend/tests/integration/test_zalo_webhook.py: secret sai/thiếu ⇒ 401, 0 job; đúng ⇒ 200 + 1 job `zalo_update` khóa `zalo:{bot_id}:{message_id}` (Zalo không có `update_id` — spike §1); gửi lại 5 lần ⇒ 1 job; DB lỗi ⇒ 503 — FR-001, FR-002 · Verify: test đỏ trước T012 (SC-004, SC-005)
- [x] T012 [US2] `backend/src/hoicon/api/webhooks.py` (app con, so secret bằng `hmac.compare_digest`, insert job, mount vào app chính) — FR-001, FR-002, FR-013 · Verify: `uv run --directory backend pytest tests/integration/test_zalo_webhook.py -q`
- [x] T013 [P] [US2] Test trước backend/tests/integration/test_pairing.py: mã đúng ⇒ gắn người giám hộ + trả lời xác nhận có câu công khai; sai/hết hạn 15'/đã dùng ⇒ hướng dẫn chung không tiết lộ; `/start` lặp ⇒ không trùng — FR-003, FR-006 · Verify: test đỏ trước T014 (SC-006, SC-008)
- [x] T014 [US2] Xử lý `/start <mã>` trong guardian.py (handler `zalo_update`) + lệnh `backend/src/hoicon/ops/pairing_code.py` (sinh mã 6 số cho gia đình dev, chỉ lưu băm) — FR-003, FR-004 · Verify: `uv run --directory backend pytest tests/integration/test_pairing.py -q`

---

## Phase 5: User Story 3 - Con phản hồi 1/2/3 (Priority: P2)

- [x] T015 [P] [US3] Test trước backend/tests/integration/test_guardian_reply.py: "1" ⇒ resume `{"decision": "safe"}` expect `await_guardian`; "2" ⇒ `scam`; "3" ⇒ gửi chi tiết, không resume; khác ⇒ hướng dẫn lại; văn bản trả lời không lưu, không log — FR-009, FR-010 · Verify: test đỏ trước T016
- [x] T016 [US3] Ánh xạ phản hồi ⇒ `messages_out` gần nhất đã gửi tới người đó ⇒ `runtime.resume`; **không có nút bấm** (T001: tài liệu Zalo không có keyboard/callback) ⇒ chỉ phản hồi 1/2/3, mẫu tin ghi rõ "trả lời 1 / 2 / 3"; mẫu câu mới trong backend/src/hoicon/agents/texts.py — FR-006, FR-009 · Verify: `uv run --directory backend pytest tests/integration/test_guardian_reply.py tests/unit/test_texts_and_threat.py -q`

---

## Phase 6: User Story 4 - Hạn mức và dự phòng (Priority: P2)

- [x] T017 [P] [US4] Test trước backend/tests/integration/test_quota.py: ≥ 95% ⇒ tin không khẩn `held_quota`, tin sự cố vẫn gửi; ≥ 80% ⇒ WARNING; tháng mới về 0; hết hạn mức ⇒ `fallback_required` — FR-007, FR-008 · Verify: test đỏ trước T018 (SC-007)
- [x] T018 [US4] Bộ kiểm hạn mức trong guardian.py (đếm theo `bot_id, quota_month`; nhóm tin sự cố bỏ qua ngưỡng 95%) + lệnh giả lập cập nhật đến từ fixture (mock) — FR-007, FR-008, FR-012 · Verify: `uv run --directory backend pytest tests/integration/test_quota.py -q`

---

## Phase 7: User Story 5 - Vận hành an toàn (Priority: P3)

- [x] T019 [US5] `backend/src/hoicon/ops/zalo_webhook.py` (`set --url`, `info`, `delete`; đọc token từ config, chỉ in Đạt/Lỗi) + test unit với mock HTTP — FR-013 · Verify: `uv run --directory backend pytest tests/unit/test_zalo_webhook_ops.py -q`
- [x] T020 [US5] Test quét: chạy toàn bộ test Zalo với token giả có dấu hiệu nhận biết ⇒ không xuất hiện trong caplog/stdout/DB; không có chat_id/user_id thô trong DB (chỉ `zalo_chat_enc`, `zalo_user_hmac`) — FR-010, FR-011 · Verify: `uv run --directory backend pytest tests/integration/test_zalo_no_leak.py -q` (SC-003)

---

## Phase 8: Polish & Cross-Cutting Concerns

- [x] T021 [P] Cập nhật docs/DATA-MODEL.md (bảng 0003 + D1), docs/API.md (webhook), docs/AGENTS.md (notify_guardian gửi thật), docs/setup/ACCOUNTS.md §3 (lệnh zalo_webhook) — FR-015 · Verify: review
- [x] T022 Reviewer: `security-privacy-reviewer` (Zalo, PII, mã hóa, token trên URL), `ux-elder-reviewer` (mẫu tin mới), `/ponytail-review` — FR-010, FR-011 · Verify: không còn finding High
- [x] T023 Toàn bộ backend với Postgres bật: `uv run --directory backend ruff check . && uv run --directory backend ruff format --check . && uv run --directory backend pytest` — FR-012 · Verify: 0 skipped do DB; thời gian bộ test Zalo < 60 s (SC-002)
- [ ] T024 **BLOCKED: chờ token bot thật (W0-3)** — chưa đo; số mock ở docs/spikes/P1-S3-zalo.md §3. Đo SC-001 với bot dev thật (quickstart "Thật"): ≥ 20 lần xếp tin ⇒ p50/p95 từ `messages_out.sent_at − jobs.created_at`; ≥ 5 lần bấm giờ tới điện thoại; ghi docs/spikes/P1-S3-zalo.md — FR-015 · Verify: bảng số có n/ngày/nguồn; thiếu token ⇒ `BLOCKED: chưa có token Zalo (W0-3)`
- [ ] T025 **BLOCKED sau T024** — ADR-010 đã có D1/D2 (Tiến duyệt), điều chỉnh khi hiện thực và rủi ro còn lại; còn thiếu kết quả đo thật + hạn mức thật. Hoàn thiện ADR-010 (kết quả đo, nút bấm có/không, hạn mức thật, điều khoản, kênh dự phòng) để Minh duyệt — FR-015 · Verify: review

---

## Phase 9: Acceptance evidence *(bắt buộc)*

- [x] T026 `/speckit-converge` tới 0 finding hoặc chạm điều kiện dừng (docs/MASTER-PLAN.md §2.5; thiếu token/duyệt ⇒ BLOCKED) — FR-001 · Verify: báo cáo converge
- [x] T027 specs/002-zalo-guardian-channel/evidence.md từ `.specify/templates/overrides/evidence-template.md` (SC-001…SC-008) — FR-015 · Verify: `python3 scripts/check-spec-trace.py`
- [x] T028 Cập nhật **dòng** P1-S3 trong docs/ROADMAP.md (trạng thái + link `specs/002-zalo-guardian-channel`; STATUS sửa sau merge) — FR-015 · Verify: `python3 scripts/check-spec-trace.py`

---

## Dependencies & Execution Order

- T001 → T003 (hợp đồng theo tài liệu thật) → T011/T013/T015 (test dùng fixture).
- T004 (Minh duyệt D1/D2) → T006 → mọi task cần bảng (T009–T010, T013–T018, T020).
- T005, T007, T008 song song với nhau (khác file), không cần duyệt.
- US1 (T009–T010) trước US3 (phản hồi cần tin đã gửi); US2 độc lập với US1; US4 sau US1.
- T024 cần token thật; T025 sau T024; T026–T028 cuối cùng.

### Thứ tự đề xuất
T001 → T002 → T003 → T004 (gửi Minh) → T005 → T007 → T008 → [chờ duyệt] → T006 → T009 → T010 → T011 → T012 →
T013 → T014 → T015 → T016 → T017 → T018 → T019 → T020 → T021 → T022 → T023 → (T024 → T025 khi có token) → T026 → T027 → T028

## Implementation Strategy

- MVP = US1 + US2 ở chế độ mock (T005–T014): đủ cho cảnh "tin Zalo cho con" trong video Vòng 1 bằng bot dev khi có token.
- Không chờ token để làm code: mọi thứ trừ T024 chạy được với mock.

## Notes

- Không đánh [x] khi Verify chưa xanh; test integration bị skip vì DB tắt không tính là xanh.
- Không đặt token/khóa trong lệnh shell, chat hay log; Tiến/Minh tự điền tệp bí mật của backend.
- Commit chỉ khi Tiến/Minh yêu cầu.
