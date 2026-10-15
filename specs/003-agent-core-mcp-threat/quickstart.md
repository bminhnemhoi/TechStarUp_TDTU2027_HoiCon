# Quickstart — spec 003 (làn B, từ gốc repo)

```bash
docker compose -f infra/compose.dev.yml up -d
uv run --directory backend alembic upgrade head                     # có migration 0004

# 1. Nạp danh sách đe dọa demo (số hư cấu) — idempotent; cần HOICON_PHONE_PEPPER_1 trong backend/.env
uv run --directory backend python -m hoicon.ops.threat_list load data/threat_seed.demo.json   # thêm 1 · cập nhật 0
uv run --directory backend python -m hoicon.ops.threat_list load data/threat_seed.demo.json   # thêm 0 · cập nhật 1

# 2. Tạo token cho /mcp/threat — token in MỘT lần; TỰ dán dòng HOICON_MCP_THREAT_CLIENTS=… vào backend/.env
uv run --directory backend python -m hoicon.ops.mcp_token new --client claude-team

# 3. Chạy API rồi gọi MCP
uv run --directory backend uvicorn hoicon.api.main:app --port 18000 --loop asyncio:SelectorEventLoop
H1=aa1b1fcd5c51853e998738c59cffa5a4d95bd39ef7ef3b6d905c9c6c3af987e4          # h1 của số HƯ CẤU flagged_caller
curl -s http://127.0.0.1:18000/mcp/threat/ -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"lookup_phone","arguments":{"h1":"'$H1'"}}}'
# không có/sai token ⇒ 401; vượt 30 yêu cầu/phút ⇒ 429 + Retry-After

# 4. So model (không khóa API ⇒ llm_mode "fallback"; có khóa ⇒ số thật)
uv run --directory backend python -m hoicon.agents.spike bench --n 20 --model claude-haiku-4-5 --json /tmp/h45.json
uv run --directory backend python -m hoicon.agents.spike bench --n 20 --model claude-haiku-5-5 --json /tmp/h55.json

# 5. Cổng chất lượng
uv run --directory backend ruff check . && uv run --directory backend ruff format --check .
uv run --directory backend pytest -q
HOICON_EVAL_DATABASE_URL=… HOICON_PHONE_PEPPER_1=<khóa giả> uv run --directory backend hoicon-eval --suite smoke --compare baseline
python3 scripts/check-spec-trace.py
```

Test dùng khóa băm GIẢ (`tests/integration/conftest.py::fake_pepper`) và token ngẫu nhiên sinh trong test, không đọc `.env`.
