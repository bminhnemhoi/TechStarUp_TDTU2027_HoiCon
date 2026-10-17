---

description: "Task list template for feature implementation (HỏiCon)"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: **BẮT BUỘC** ở HỏiCon (Hiến chương VII + Definition of Done trong CLAUDE.md). Viết test trước, thấy test đỏ rồi
mới code. Đổi prompt/đồ thị ⇒ có task chạy `run-eval smoke`; đổi cảm biến ⇒ có task chạy `emu-scenario.py` AVD 36 + 34;
đổi UI ⇒ có task chụp ảnh 100% + 200% và gọi `ux-elder-reviewer`.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description — FR-xxx · Verify: \`lệnh\``

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions
- **FR-xxx**: mã yêu cầu trong spec.md mà task đáp ứng — mọi FR phải xuất hiện ở ít nhất 1 task
  (`scripts/check-spec-trace.py` kiểm)
- **Verify**: lệnh chạy được để chứng minh task xong (test cụ thể, lint, kịch bản máy ảo…). Task không có lệnh kiểm
  (vd. tài liệu) ghi `Verify: review`
- Làn: đường dẫn `apps/android/**` = làn A; `backend/**`, `apps/web/**`, `infra/**` = làn B. Một tasks.md không trộn
  hai làn trong cùng phase trừ khi hợp đồng `docs/schemas/` đã merge trước

## Path Conventions (monorepo HỏiCon)

- Android: `apps/android/{rules,app,demobank,latency}/src/...`
- Backend: `backend/src/hoicon/{api,agents,jobs,domain,db,mcp_servers}/`, test `backend/tests/{unit,integration,contract}/`
- Web: `apps/web/src/...` · Hợp đồng: `docs/schemas/` · Dữ liệu: `data/` · Script: `scripts/`

<!--
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.
  The /speckit-tasks command MUST replace these with actual tasks based on spec.md, plan.md,
  data-model.md, contracts/. DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Hợp đồng và khung — merge `docs/schemas/` trước khi hai làn code

- [ ] T001 Add/extend JSON Schema + fixture in docs/schemas/[name].v1.json — FR-001 · Verify: `uv run --directory backend pytest tests/contract -q`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T002 Alembic migration in backend/migrations/versions/[date]_[nnnn]_[slug].py — FR-002 · Verify: `uv run --directory backend alembic upgrade head && uv run --directory backend pytest tests/integration -q`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 (write FIRST, ensure they FAIL) ⚠️

- [ ] T010 [P] [US1] Contract test for [endpoint] in backend/tests/contract/test_[name].py — FR-003 · Verify: `uv run --directory backend pytest backend/tests/contract/test_[name].py -q` (đỏ trước khi code)

### Implementation for User Story 1

- [ ] T012 [US1] Implement [feature] in backend/src/hoicon/[module]/[file].py — FR-003 · Verify: `uv run --directory backend pytest -q && uv run --directory backend ruff check .`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N-1: Polish & Cross-Cutting Concerns

- [ ] TXXX [P] Update docs liên quan (docs/API.md, docs/DATA-MODEL.md, docs/AGENTS.md…) — Verify: review
- [ ] TXXX Reviewer: `security-privacy-reviewer` (nếu đụng PII/LLM/manifest/Zalo), `ux-elder-reviewer` (nếu có màn hình), `/ponytail-review` — Verify: không còn finding High
- [ ] TXXX Run quickstart.md validation — Verify: các bước trong quickstart.md chạy được

---

## Phase N: Acceptance evidence *(bắt buộc)*

**Purpose**: Chống "xong trên giấy" — không đánh ☑ ROADMAP khi phase này chưa xong

- [ ] TXXX Chạy `/speckit-converge` tới khi 0 finding hoặc chạm điều kiện dừng (docs/MASTER-PLAN.md §2.5; finding bị chặn ⇒ BLOCKED trong evidence.md) — Verify: báo cáo converge
- [ ] TXXX Chạy cổng các tầng bị đụng tới (backend pytest + ruff · `:rules:test :app:lintDebug` · web typecheck/lint/test · hook test · emu-scenario · run-eval smoke) — Verify: output dán vào evidence.md
- [ ] TXXX Viết specs/[###-feature-name]/evidence.md từ `.specify/templates/overrides/evidence-template.md` (mỗi SC-xxx có số đo + nguồn) — Verify: `python3 scripts/check-spec-trace.py`
- [ ] TXXX Cập nhật **dòng task** của spec trong docs/ROADMAP.md (trạng thái + link spec; khối STATUS sửa sau merge ở checkout chính) — Verify: `python3 scripts/check-spec-trace.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — hợp đồng merge trước
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion; sequential by priority unless [P]
- **Polish → Acceptance evidence**: cuối cùng, không được bỏ

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Schema/models before services, services before endpoints/UI
- Story complete (Verify xanh) before moving to next priority

### Parallel Opportunities

- [P] = khác file, không phụ thuộc task chưa xong. Song song giữa hai làn A/B dùng hai worktree (docs/MASTER-PLAN.md §5);
  trong một worktree, một phiên Claude làm tuần tự

---

## Notes

- Mỗi task nhỏ đủ để xong trong ≤ 1/2 ngày; task mơ hồ ⇒ tách nhỏ
- Không đánh dấu [x] khi Verify chưa chạy xanh; bước không chạy được ghi SKIPPED/UNAVAILABLE kèm lý do trong evidence.md
- Commit chỉ khi Minh/Tiến yêu cầu (CLAUDE.md)
