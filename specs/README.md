# specs/ — đặc tả theo Spec Kit

Mỗi thư mục `NNN-slug/` là một tính năng làm theo Spec-Driven Development (`spec.md` → `plan.md` → `tasks.md` →
`evidence.md`). **Số spec được cấp trước** trong [`docs/MASTER-PLAN.md`](../docs/MASTER-PLAN.md) §3 — không tự đặt số mới.

- Cách làm một tính năng: Master Plan §6. Làm song song bằng worktree: §5.
- Nguyên tắc phải qua: [`.specify/memory/constitution.md`](../.specify/memory/constitution.md).
- Trạng thái task vẫn ở [`docs/ROADMAP.md`](../docs/ROADMAP.md); dòng task link tới thư mục spec khi spec được tạo.
- Kiểm truy vết: `python3 scripts/check-spec-trace.py` (CI chạy trên mọi PR đụng `specs/`).
