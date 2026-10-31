# Quickstart: kiểm tay spec 002 (worktree `../hoicon-wt/server`)

```bash
cd ~/Projects/hoicon-wt/server
uv sync --directory backend
docker compose -f infra/compose.dev.yml up -d          # Postgres 15432 (dùng chung với làn A)
uv run --directory backend alembic upgrade head          # có migration 0003
# (Minh/Tiến tự chạy một lần, Claude không ghi .env) init_env --new-data-key: nối HOICON_DATA_KEY_1 vào .env cũ — ACCOUNTS.md §3
uv run --directory backend pytest                       # chế độ mock, không cần token

# Mock đầu–cuối (không token, không mạng; tin "gửi" bằng mock ghi messages_out.error='mock')
uv run --directory backend python -m hoicon.ops.pairing_code --family dev-gia-dinh      # in mã ghép 6 số (15 phút, một lần)
uv run --directory backend python -m hoicon.ops.zalo_simulate "/start <mã>"             # người dùng hư cấu fixture-user-0001
uv run --directory backend python -m hoicon.agents.spike demo --family dev-gia-dinh     # mở sự cố ⇒ tin vào MockZaloClient + bảng độ trễ
uv run --directory backend python -m hoicon.ops.zalo_simulate 1                         # trả lời "1" (cần sự cố đang chờ)

# Thật (cần token bot dev trong tệp bí mật backend — Tiến/Minh tự đặt; HOICON_ZALO_MODE=live)
uv run --directory backend python -m hoicon.ops.check_keys                       # Zalo token: Đạt
uv run --directory backend uvicorn hoicon.api.webhooks:app --port 18080 --loop asyncio:SelectorEventLoop   # chỉ app webhook
cloudflared tunnel --url http://127.0.0.1:18080                                  # lấy URL https tạm
uv run --directory backend python -m hoicon.ops.zalo_webhook set --url <https…>  # chỉ in Đạt/Lỗi
uv run --directory backend python -m hoicon.ops.zalo_webhook info
#   nhắn /start <mã> cho bot từ Zalo của Tiến/Minh; chạy `spike demo --family dev-gia-dinh` ≥ 20 lần ⇒ đo SC-001
#   (bảng "tin gửi người giám hộ" in `jobs.created_at → messages_out.sent_at`)
```
Ghi mọi số vào `evidence.md` (mock ghi nhãn "mock").
