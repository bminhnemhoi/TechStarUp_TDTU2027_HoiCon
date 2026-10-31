# Implementation Plan: [FEATURE]

**Branch**: `[feat/###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!-- Stack cố định của HỏiCon — chỉ sửa dòng nào feature này dùng khác đi. -->

**Language/Version**: Kotlin 2.4 (Android, minSdk 29, target/compileSdk 36) · Python 3.12 (`uv`) · TypeScript strict (Next.js)

**Primary Dependencies**: Compose + Material 3 · FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, psycopg 3, LangGraph
(`AsyncPostgresSaver`), MCP Python SDK · Next.js, Tailwind v4, shadcn/ui — thêm thư viện mới phải nêu lý do (Hiến chương VIII)

**Storage**: Postgres 17 + pgvector (dev cổng 15432; hàng đợi job, checkpoint, vector) · Android: Room + Tink (từ P2-05)

**Testing**: `uv run --directory backend pytest` + `ruff` · `apps/android/gradlew -p apps/android :rules:test :app:lintDebug` ·
`pnpm --dir apps/web typecheck lint test` · `node --test ".claude/hooks/test/*.test.mjs"` · `scripts/emu-scenario.py` ·
`run-eval smoke` (khi có)

**Target Platform**: Android 10–16 (AVD hc-api36/34/29 + máy thật qua Firebase Test Lab) · Linux VPS (docker compose + Caddy)

**Project Type**: monorepo mobile + API + web

**Performance Goals**: [vd. SafePause p95 ≤ 3 s · Zalo giai đoạn 1 p95 ≤ 10 s · một lượt tác tử p95 ≤ 8 s]

**Constraints**: offline cho đường găng · LLM timeout ≤ 4 s · hạn mức Zalo 3.000 tin/tháng · RAM máy dev thấp

**Scale/Scope**: thí điểm 20–30 gia đình (gate M3/G3)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Nguồn: `.specify/memory/constitution.md`.

| # | Nguyên tắc | Feature này đụng tới? | Đạt / cách đảm bảo |
|---|---|---|---|
| I | Dừng an toàn offline ≤ 3 s, không chặn vĩnh viễn | [Có/Không] | |
| II | Riêng tư: không PII thô, quyền Android cấm | | |
| III | LLM chỉ nâng, qua `llm_router` | | |
| IV | Công khai AI, đồng ý chỉ ghi thêm, `is_drill`/`is_demo` | | |
| V | Hợp đồng trước (`docs/schemas/`), migration bất biến, `IncidentService` | | |
| VI | UX người cao tuổi | | |
| VII | Bằng chứng trung thực (nguồn số đo) | | |
| VIII | Ít code nhất, tái sử dụng trước | | |
| IX | Chặn phát hành | | |

## Tái sử dụng *(mandatory — điền TRƯỚC khi thiết kế mới)*

| Cần gì | Đã có ở đâu | Dùng lại / mở rộng / viết mới (lý do) |
|---|---|---|
| [vd. hàng đợi job] | `backend/src/hoicon/jobs/queue.py` | dùng lại |
| [vd. che PII] | `backend/src/hoicon/domain/pii.py` | dùng lại |

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── spec.md · plan.md · research.md (chỉ khi có câu hỏi mở) · quickstart.md
├── data-model.md        # chỉ phần CHÊNH LỆCH, trỏ docs/DATA-MODEL.md
├── contracts/README.md  # liệt kê schema — schema mới viết thẳng vào docs/schemas/
├── tasks.md             # /speckit-tasks
├── checklists/          # /speckit-checklist (privacy / elder-ux / release-block)
└── evidence.md          # bằng chứng nghiệm thu (mẫu: .specify/templates/overrides/evidence-template.md)
```

### Source Code (repository root)

<!-- Giữ những dòng feature này đụng tới, xóa phần còn lại. Làn A = Android, làn B = backend/web. -->

```text
apps/android/rules/        # [A] luật tất định JVM thuần + test (không cần máy ảo)
apps/android/app/          # [A] Lính gác: sensing/, pause/, ui/
apps/android/demobank/     # [A] app ngân hàng mẫu
apps/android/latency/      # [A] bộ đo độ trễ cho Firebase Test Lab
backend/src/hoicon/        # [B] api/ agents/ jobs/ domain/ db/ mcp_servers/
backend/migrations/        # [B] Alembic — chỉ làn B tạo migration
backend/tests/             # [B] unit/ integration/ contract/
apps/web/src/              # [B] Next.js
docs/schemas/              # hợp đồng dùng chung — merge TRƯỚC khi hai làn code
data/                      # bank_apps, scenarios, fixtures (số hư cấu)
scripts/                   # emu-*, gen-*, ftl-latency
```

**Structure Decision**: [Ghi các thư mục thật feature này đụng tới]

## Thiết kế & trade-off

[Các phương án đã cân nhắc, phương án chọn, lý do; rủi ro và cách giảm. Đổi quyết định đã chốt ⇒ ADR mới.]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
