#!/usr/bin/env bash
# Triển khai HỏiCon lên VPS (spec 012). Chạy TRÊN VPS, từ bất kỳ thư mục nào của bản sao repo:
#   bash scripts/deploy-vps.sh              # kiểm biến → build → sao lưu (nếu đã có dữ liệu) → migrate → nạp container → kiểm /readyz
#   bash scripts/deploy-vps.sh --check      # chỉ kiểm biến + cấu hình compose, KHÔNG đổi gì trên máy
# Tùy chọn: --env-file <tệp> (mặc định infra/.env.prod) · --skip-backup · --check-url <URL> · --insecure (chứng chỉ tự ký)
# Hướng dẫn: docs/setup/VPS-DEPLOYMENT.md. Script KHÔNG bao giờ in giá trị khóa (chỉ tên biến) và không `source` tệp biến.
# Thử cục bộ: HOICON_COMPOSE_OVERRIDE=<tệp compose bổ sung> (đổi cổng/tên container); không dùng ở VPS thật.
# -E: bẫy ERR cũng chạy khi lệnh hỏng nằm trong hàm (dc build/up/run); thiếu thì script thoát mà không in hướng dẫn gỡ lỗi.
set -Eeuo pipefail
cd "$(dirname "$0")/.."

ENV_FILE="infra/.env.prod"
SKIP_BACKUP=0
CHECK_ONLY=0
CHECK_URL=""
INSECURE=0

ROLLOUT=0 # =1 khi bắt đầu thay đổi máy: mọi lỗi từ đó in kèm nhật ký backend
show_logs() {
  echo >&2
  echo "THẤT BẠI — bản ${HOICON_RELEASE:-?} CHƯA hoàn tất rollout. Nhật ký backend gần nhất:" >&2
  # Bỏ dòng healthcheck (mỗi 15 giây một dòng) kẻo che mất lỗi thật.
  { dc logs --no-log-prefix --tail=300 backend 2>&1 | grep -v 'GET /readyz' | tail -40 | sed 's/^/  | /' >&2; } || true
  cat >&2 << 'EOF'

Gỡ lỗi: docker compose -f infra/compose.prod.yml --env-file infra/.env.prod ps | logs <dịch vụ>
Quay lui: đặt HOICON_RELEASE=<bản trước> rồi `docker compose ... up -d` (xem mục "Quay lui" ở VPS-DEPLOYMENT.md).
Migration chỉ đi tới: nếu migrate đã chạy, khôi phục dữ liệu từ bản sao lưu thay vì hạ migration.
EOF
}
die() {
  echo "LỖI: $*" >&2
  if [ "$ROLLOUT" = 1 ]; then show_logs; fi
  exit 1
}
step() { printf '\n==> %s\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --check) CHECK_ONLY=1 ;;
    --skip-backup) SKIP_BACKUP=1 ;;
    --insecure) INSECURE=1 ;;
    --env-file) ENV_FILE="${2:?--env-file cần đường dẫn}"; shift ;;
    --check-url) CHECK_URL="${2:?--check-url cần URL}"; shift ;;
    -h | --help) sed -n '2,8p' "$0"; exit 0 ;;
    *) die "tùy chọn lạ: $1 (xem --help)" ;;
  esac
  shift
done

# Đọc tệp biến không `source` (get, envfile_check_mode): dùng chung với scripts/backup-vps.sh.
# shellcheck source=lib/envfile.sh
source "$(dirname "$0")/lib/envfile.sh"

COMPOSE=(docker compose -f infra/compose.prod.yml)
if [ -n "${HOICON_COMPOSE_OVERRIDE:-}" ]; then
  COMPOSE+=(-f "$HOICON_COMPOSE_OVERRIDE")
fi
COMPOSE+=(--env-file "$ENV_FILE")
dc() { "${COMPOSE[@]}" "$@"; }

# ---------------------------------------------------------------------------------------------------------------------
# 1. Kiểm công cụ và tệp biến
# ---------------------------------------------------------------------------------------------------------------------
step "Kiểm công cụ"
command -v docker > /dev/null || die "chưa cài docker"
docker compose version > /dev/null 2>&1 || die "chưa có 'docker compose' (plugin v2)"
command -v curl > /dev/null || die "chưa cài curl"
[ -f "$ENV_FILE" ] || die "không thấy $ENV_FILE — sao chép infra/env.prod.example thành $ENV_FILE rồi điền (xem docs/setup/VPS-DEPLOYMENT.md)"
envfile_check_mode || exit 1

step "Kiểm biến bắt buộc (chỉ in tên biến, không in giá trị)"
errors=()
# need <TÊN> <regex> <gợi ý>: thiếu hoặc sai định dạng ⇒ ghi lỗi.
need() {
  local v
  v=$(get "$1")
  if [ -z "$v" ]; then
    errors+=("$1: thiếu — $3")
  elif ! [[ $v =~ $2 ]]; then
    errors+=("$1: sai định dạng — $3")
  fi
}
HEX64='^[0-9a-fA-F]{64}$'
need POSTGRES_PASSWORD '^[A-Za-z0-9]{24,}$' "chữ và số, ≥ 24 ký tự (sinh: openssl rand -hex 24)"
need HOICON_DOMAIN '^([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z0-9]([a-z0-9-]*[a-z0-9])?$' "tên miền chữ thường, vd app.hoicon.vn (không kèm https://)"
need HOICON_ACME_EMAIL '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$' "email nhận cảnh báo chứng chỉ"
need HOICON_DEVICE_JWT_SECRET '^.{32,}$' "≥ 32 ký tự (sinh: openssl rand -hex 32)"
need HOICON_ZALO_WEBHOOK_SECRET '^[^<>]{8,256}$' "8–256 ký tự, đúng giá trị đã đặt khi setWebhook"
need HOICON_ZALO_BOT_TOKEN '^[^<>[:space:]]{8,}$' "token bot Zalo thật (docs/setup/ACCOUNTS.md)"

# Pepper, khóa dữ liệu, khóa sao lưu: hex 64 ký tự, đúng `kid` đang dùng; compose luôn đòi khóa 1.
pepper_kid=$(get HOICON_PHONE_PEPPER_KID); pepper_kid=${pepper_kid:-1}
backup_kid=$(get HOICON_BACKUP_KEY_KID); backup_kid=${backup_kid:-1}
data_kid=$(get HOICON_DATA_KEY_KID); data_kid=${data_kid:-1}
[[ $pepper_kid =~ ^[12]$ ]] || errors+=("HOICON_PHONE_PEPPER_KID: chỉ chấp nhận 1 hoặc 2")
[[ $backup_kid =~ ^[12]$ ]] || errors+=("HOICON_BACKUP_KEY_KID: chỉ chấp nhận 1 hoặc 2")
[ "$data_kid" = 1 ] || errors+=("HOICON_DATA_KEY_KID: backend mới có HOICON_DATA_KEY_1, đặt 1")
need HOICON_PHONE_PEPPER_1 "$HEX64" "hex 64 ký tự (sinh: openssl rand -hex 32)"
need HOICON_DATA_KEY_1 "$HEX64" "hex 64 ký tự (sinh: openssl rand -hex 32)"
if [ "$pepper_kid" != 1 ]; then need "HOICON_PHONE_PEPPER_${pepper_kid}" "$HEX64" "pepper của kid ${pepper_kid} đang dùng"; fi
need "HOICON_BACKUP_KEY_${backup_kid}" "$HEX64" "khóa sao lưu RIÊNG, hex 64 ký tự"

# Mỗi khóa một mục đích: dùng chung một giá trị cho hai việc làm mất ý nghĩa của việc tách khóa.
declare -A seen=()
for name in HOICON_PHONE_PEPPER_1 HOICON_DATA_KEY_1 "HOICON_BACKUP_KEY_${backup_kid}" HOICON_DEVICE_JWT_SECRET; do
  v=$(get "$name")
  [ -n "$v" ] || continue
  if [ -n "${seen[$v]:-}" ]; then
    errors+=("$name trùng giá trị với ${seen[$v]}: mỗi khóa phải sinh riêng")
  else
    seen[$v]=$name
  fi
done
unset seen v

env_value=$(get HOICON_ENV)
if [ -n "$env_value" ] && [ "$env_value" != prod ]; then
  echo "LƯU Ý: $ENV_FILE có HOICON_ENV=$env_value — bị bỏ qua, compose luôn ép HOICON_ENV=prod."
fi

if [ ${#errors[@]} -gt 0 ]; then
  printf 'LỖI cấu hình:\n' >&2
  printf '  - %s\n' "${errors[@]}" >&2
  exit 1
fi
echo "Các biến bắt buộc hợp lệ."

step "Kiểm cấu hình compose"
dc config -q || die "compose không hợp lệ (xem thông báo trên)"
echo "compose hợp lệ."

if [ "$CHECK_ONLY" = 1 ]; then
  echo
  echo "--check: xong, chưa đổi gì trên máy."
  exit 0
fi

DOMAIN=$(get HOICON_DOMAIN)
[ -n "$CHECK_URL" ] || CHECK_URL="https://${DOMAIN}"
CURL=(curl -sS --max-time 10)
if [ "$INSECURE" = 1 ]; then CURL+=(-k); fi

HOICON_RELEASE=$(git rev-parse --short=12 HEAD 2> /dev/null || date +%Y%m%d%H%M%S)
if [ -n "$(git status --porcelain 2> /dev/null || true)" ]; then
  HOICON_RELEASE="${HOICON_RELEASE}-dirty"
  echo "LƯU Ý: bản sao có thay đổi chưa commit ⇒ bản phát hành ${HOICON_RELEASE} khó tái lập."
fi
export HOICON_RELEASE

on_error() {
  local code=$?
  trap - ERR
  show_logs
  exit "$code"
}
trap on_error ERR
ROLLOUT=1

# ---------------------------------------------------------------------------------------------------------------------
# 2. Build và khởi động Postgres
# ---------------------------------------------------------------------------------------------------------------------
step "Build ảnh backend + web (bản ${HOICON_RELEASE})"
dc build --pull

step "Khởi động Postgres"
dc up -d --wait --wait-timeout 120 postgres

# ---------------------------------------------------------------------------------------------------------------------
# 3. Sao lưu trước khi migrate (chỉ khi DB đã có dữ liệu của bản trước)
# ---------------------------------------------------------------------------------------------------------------------
has_data=$(dc exec -T postgres psql -U hoicon -d hoicon -qAt -c "select to_regclass('public.alembic_version') is not null" | tr -d '[:space:]')
if [ "$has_data" = t ]; then
  if [ "$SKIP_BACKUP" = 1 ]; then
    echo "LƯU Ý: bỏ qua sao lưu trước migrate theo --skip-backup."
  else
    step "Sao lưu mã hóa trước khi migrate"
    command -v uv > /dev/null || die "cần 'uv' trên VPS để chạy sao lưu (https://docs.astral.sh/uv/) — hoặc dùng --skip-backup nếu bạn đã sao lưu"
    # Thất bại ⇒ ERR trap dừng toàn bộ: KHÔNG migrate khi chưa có bản sao lưu. Khóa sao lưu và đường tới Postgres do
    # backup-vps.sh dựng cho riêng tiến trình sao lưu (không vào container ứng dụng).
    bash scripts/backup-vps.sh --env-file "$ENV_FILE"
  fi
else
  echo "Postgres còn trống (lần triển khai đầu): không cần sao lưu trước migrate."
fi

# ---------------------------------------------------------------------------------------------------------------------
# 4. Migrate TRƯỚC khi nạp container mới
# ---------------------------------------------------------------------------------------------------------------------
step "alembic upgrade head"
dc run --rm --no-deps -T backend alembic upgrade head

# ---------------------------------------------------------------------------------------------------------------------
# 5. Nạp container mới và chờ khỏe
# ---------------------------------------------------------------------------------------------------------------------
step "Nạp container"
dc up -d --wait --wait-timeout 300 --remove-orphans

# ---------------------------------------------------------------------------------------------------------------------
# 6. Chỉ hoàn tất khi /readyz QUA Caddy trả đúng 200 (chứng chỉ có thể mất vài chục giây ở lần đầu)
# ---------------------------------------------------------------------------------------------------------------------
step "Kiểm ${CHECK_URL}/readyz"
code=000
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
for attempt in $(seq 1 24); do
  code=$("${CURL[@]}" -o "$tmp" -w '%{http_code}' "${CHECK_URL}/readyz" 2> /dev/null || true)
  [ "$code" = 200 ] && break
  echo "  lần ${attempt}/24: HTTP ${code} — thử lại sau 5 giây"
  sleep 5
done
body=$(cat "$tmp" 2> /dev/null || true)
if [ "$code" != 200 ]; then
  echo "  /readyz cuối cùng: HTTP ${code} ${body}" >&2
  die "/readyz không trả 200 — rollout KHÔNG hoàn tất"
fi
echo "  /readyz: HTTP 200 ${body}"

web_code=$("${CURL[@]}" -o /dev/null -w '%{http_code}' "${CHECK_URL}/login" || true)
[ "$web_code" = 200 ] || die "trang web /login trả HTTP ${web_code} (mong 200) — kiểm container web và Caddy"
echo "  web /login: HTTP 200"
docs_code=$("${CURL[@]}" -o /dev/null -w '%{http_code}' "${CHECK_URL}/docs" || true)
[ "$docs_code" = 404 ] || die "/docs trả HTTP ${docs_code} (mong 404): tài liệu API không được phơi ra Internet"
echo "  /docs: HTTP 404 (đã đóng)"

trap - ERR
echo
echo "XONG: bản ${HOICON_RELEASE} đang chạy tại ${CHECK_URL}."
echo "Việc tiếp: đặt webhook Zalo tới ${CHECK_URL}/webhooks/zalo/<bot_id> và bật lịch sao lưu (VPS-DEPLOYMENT.md §7–8)."
