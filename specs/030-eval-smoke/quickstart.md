# Quickstart: kiểm tay spec 030 (worktree `../hoicon-wt/server`)

```bash
cd ~/Projects/hoicon-wt/server
uv sync --directory backend
docker compose -f infra/compose.dev.yml up -d                      # Postgres 15432

# DB eval riêng (một lần). Tên user/DB theo infra/compose.dev.yml; không đọc .env — Tiến tự điền mật khẩu nếu cần.
docker compose -f infra/compose.dev.yml exec db createdb -U hoicon hoicon_eval   # đã có ⇒ báo "already exists", bỏ qua
export HOICON_EVAL_DATABASE_URL=postgresql+psycopg://hoicon:<mật khẩu dev>@127.0.0.1:15432/hoicon_eval
HOICON_DATABASE_URL=$HOICON_EVAL_DATABASE_URL uv run --directory backend alembic upgrade head

uv run --directory backend pytest -q                                # gồm test eval + đột biến
time uv run --directory backend hoicon-eval --suite smoke --compare baseline   # ~5–6 s (< 60 s), exit 0
ls backend/eval/reports/                                            # <ngày>-smoke.json + .md (git bỏ qua)

# Thử rào: bước "gỡ raise_only / câu công khai AI / bộ lọc tóm tắt" đã được tự động hóa:
uv run --directory backend pytest tests/integration/test_eval_mutations.py -q   # mỗi đột biến ⇒ trượt đúng ca, đúng loại
uv run --directory backend hoicon-eval --suite full; echo $?        # exit 2: "chưa có — spec 036"
```

Mã thoát: 0 đạt · 1 trượt (vi phạm an toàn, lệch kỳ vọng, hoặc tụt quá ngưỡng so baseline) · 2 lỗi dùng/cấu hình
(thiếu `HOICON_EVAL_DATABASE_URL`, `HOICON_ENV=prod`, DB trùng DB ứng dụng mà không có `--shared-db-ok`, suite chưa có).

Baseline đầu tiên (T018): `uv run --directory backend hoicon-eval --suite smoke --write-baseline` — chỉ chạy tay, lượt phải đạt.
Ghi thời gian 3 lần chạy + chỉ số vào `evidence.md`.
