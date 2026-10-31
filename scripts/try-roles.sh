#!/usr/bin/env bash
# scripts/try-roles.sh — Thử infra/postgres/roles.sql trên một Postgres TẠM (spec 012 T017, FR-001).
#
# Vì sao không thử trên DB dev: role `hoicon_app` có thể đã tồn tại với mật khẩu của người khác, nên bài thử sẽ đụng hoặc
# bị bỏ qua. Ở đây dựng một container riêng (cổng 15433, xóa khi xong), nên luôn chạy được và không đụng DB dev.
#
#   1. migration + AsyncPostgresSaver.setup() bằng role CHỦ        4. test_db_roles.py (không bị bỏ qua)
#   2. áp roles.sql (và áp lần hai: phải chạy lại được)           5. một lượt đồ thị + job dưới `hoicon_app`
#   3. API dưới `hoicon_app`: /healthz, /readyz = 200              6. dọn container
# Mật khẩu sinh ngẫu nhiên cho mỗi lần chạy, chỉ nằm trong môi trường của script này.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

NAME="${T017_CONTAINER:-hoicon-db-t017}"
PORT="${T017_PORT:-15433}"
API_PORT="${T017_API_PORT:-18003}"
OWNER_PW="$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')"
APP_PW="$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')"
OWNER_URL="postgresql+psycopg://hoicon:${OWNER_PW}@127.0.0.1:${PORT}/hoicon"
APP_URL="postgresql+psycopg://hoicon_app:${APP_PW}@127.0.0.1:${PORT}/hoicon"
API_PID=""
SIGNING_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
step() { echo -e "\n${YELLOW}[$1/6] $2${NC}"; }
ok() { echo -e "${GREEN}✓ $1${NC}"; }
cleanup() {
  [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null || true
  docker rm -f "$NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" -e POSTGRES_USER=hoicon -e POSTGRES_PASSWORD="$OWNER_PW" -e POSTGRES_DB=hoicon \
  -e TZ=UTC -p "127.0.0.1:${PORT}:5432" -v "$ROOT_DIR/infra/postgres/init:/docker-entrypoint-initdb.d:ro" \
  pgvector/pgvector:pg17 >/dev/null
for _ in $(seq 1 60); do
  docker exec "$NAME" pg_isready -U hoicon -d hoicon >/dev/null 2>&1 && break
  sleep 1
done
# Lần khởi động đầu Postgres còn chạy init rồi khởi động lại: đợi lần sẵn sàng thứ hai ổn định.
sleep 3
docker exec "$NAME" pg_isready -U hoicon -d hoicon >/dev/null

step 1 "Migration + AsyncPostgresSaver.setup() bằng role chủ"
export HOICON_DATABASE_URL="$OWNER_URL"
uv run --directory backend alembic upgrade head
uv run --directory backend python -c "
import asyncio
from hoicon.agents.runtime import open_checkpointer
from hoicon.config import get_settings

async def main() -> None:
    async with open_checkpointer(get_settings().database_url.get_secret_value()):
        pass  # open_checkpointer gọi AsyncPostgresSaver.setup()

asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
"
ok "bảng ứng dụng + bảng checkpoint đã có"

step 2 "Áp roles.sql (hai lần: chạy lại được) và đặt mật khẩu tạm cho hoicon_app"
docker exec -i "$NAME" psql -U hoicon -d hoicon -v ON_ERROR_STOP=1 -q <infra/postgres/roles.sql
docker exec -i "$NAME" psql -U hoicon -d hoicon -v ON_ERROR_STOP=1 -q <infra/postgres/roles.sql
docker exec "$NAME" psql -U hoicon -d hoicon -v ON_ERROR_STOP=1 -q -c "ALTER ROLE hoicon_app PASSWORD '${APP_PW}'"
# Bảng do LangGraph tạo bằng role chủ cũng phải cấp quyền: chạy lại roles.sql sau setup() (docs ghi rõ bước này).
docker exec -i "$NAME" psql -U hoicon -d hoicon -v ON_ERROR_STOP=1 -q <infra/postgres/roles.sql
ok "roles.sql áp được, chạy lại được"

step 3 "API dưới hoicon_app: /healthz và /readyz"
HOICON_DATABASE_URL="$APP_URL" HOICON_DEVICE_JWT_SECRET="$SIGNING_KEY" uv run --directory backend uvicorn hoicon.api.main:app --port "$API_PORT" \
  --loop asyncio:SelectorEventLoop >/tmp/hoicon-t017-api.log 2>&1 &
API_PID=$!
for _ in $(seq 1 40); do
  curl -fsS "http://127.0.0.1:${API_PORT}/healthz" >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS "http://127.0.0.1:${API_PORT}/healthz" >/dev/null
READY="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${API_PORT}/readyz")"
[ "$READY" = "200" ] || { echo "readyz = $READY (xem /tmp/hoicon-t017-api.log)"; exit 1; }
kill "$API_PID" 2>/dev/null || true
API_PID=""
ok "/readyz 200 dưới hoicon_app"

step 4 "test_db_roles.py (role chưa tồn tại ⇒ không bị bỏ qua)"
docker exec "$NAME" psql -U hoicon -d hoicon -q -c "DROP OWNED BY hoicon_app" -c "DROP ROLE hoicon_app"
HOICON_DATABASE_URL="$OWNER_URL" uv run --directory backend pytest -p no:cacheprovider -q -rs \
  tests/integration/test_db_roles.py | tee /tmp/hoicon-t017-roles.log
! grep -q "skipped" /tmp/hoicon-t017-roles.log || { echo "test_db_roles bị bỏ qua"; exit 1; }
ok "test_db_roles xanh, 0 bỏ qua"

step 5 "Một lượt đồ thị + job dưới hoicon_app"
docker exec -i "$NAME" psql -U hoicon -d hoicon -v ON_ERROR_STOP=1 -q <infra/postgres/roles.sql
docker exec "$NAME" psql -U hoicon -d hoicon -v ON_ERROR_STOP=1 -q -c "ALTER ROLE hoicon_app PASSWORD '${APP_PW}'"
HOICON_DATABASE_URL="$APP_URL" uv run --directory backend python "$ROOT_DIR/scripts/lib/roles_smoke.py"
ok "đồ thị + checkpoint + job chạy dưới hoicon_app, không thiếu quyền"

echo -e "\n${GREEN}T017: roles.sql thử xong trên Postgres tạm ${NAME}:${PORT} (đã xóa).${NC}"
