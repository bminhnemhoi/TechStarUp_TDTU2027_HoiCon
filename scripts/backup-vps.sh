#!/usr/bin/env bash
# Sao lưu mã hóa Postgres của PROD (spec 012 + 034). Chạy TRÊN VPS, từ bất kỳ thư mục nào của bản sao repo:
#   bash scripts/backup-vps.sh                       # sao lưu + xoay vòng (7 bản ngày + 4 bản tuần)
#   bash scripts/backup-vps.sh restore-check         # khôi phục bản mới nhất vào DB tạm rồi kiểm
#   bash scripts/backup-vps.sh --env-file <tệp> ...  # tệp biến khác (mặc định infra/.env.prod)
# Đây là bọc mỏng quanh scripts/backup.sh. Khác biệt duy nhất: công cụ sao lưu cần kết nối Postgres TỪ máy chủ (để xuất
# snapshot nhất quán), mà ở prod Postgres không có cổng nào xuất ra (compose.prod.yml, mạng `internal`). Script lấy IP của
# container trên mạng docker (máy chủ tới được, Internet thì không) và đặt URL kết nối cho đúng tiến trình sao lưu, cùng
# khóa sao lưu đọc từ tệp biến. Không giá trị bí mật nào xuất hiện trong argv hay bị in ra.
# Lịch hằng ngày: docs/setup/VPS-DEPLOYMENT.md §8.
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE="infra/.env.prod"
if [ "${1:-}" = "--env-file" ]; then
  ENV_FILE="${2:?--env-file cần đường dẫn}"
  shift 2
fi

# shellcheck source=lib/envfile.sh
source "$(dirname "$0")/lib/envfile.sh"

die() {
  echo "LỖI: $*" >&2
  exit 1
}

command -v docker > /dev/null || die "chưa cài docker"
command -v uv > /dev/null || die "cần 'uv' trên VPS để chạy công cụ sao lưu (https://docs.astral.sh/uv/)"
[ -f "$ENV_FILE" ] || die "không thấy $ENV_FILE"
envfile_check_mode || exit 1

CONTAINER="${HOICON_BACKUP_CONTAINER:-hoicon-db}"
ip=$(docker inspect "$CONTAINER" -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' 2> /dev/null | awk '{print $1}' || true)
[ -n "$ip" ] || die "container Postgres '$CONTAINER' không chạy (docker compose ... up -d postgres)"

password=$(get POSTGRES_PASSWORD)
[ -n "$password" ] || die "POSTGRES_PASSWORD trống trong $ENV_FILE"
kid=$(get HOICON_BACKUP_KEY_KID)
kid=${kid:-1}
key=$(get "HOICON_BACKUP_KEY_${kid}")
[ -n "$key" ] || die "thiếu HOICON_BACKUP_KEY_${kid} trong $ENV_FILE"

# `export` là lệnh nội bộ ⇒ giá trị không vào argv (ps, /proc/*/cmdline); chỉ tiến trình con này và con cháu thấy.
export HOICON_DATABASE_URL="postgresql+psycopg://hoicon:${password}@${ip}:5432/hoicon"
export HOICON_BACKUP_CONTAINER="$CONTAINER"
export HOICON_BACKUP_KEY_KID="$kid"
export "HOICON_BACKUP_KEY_${kid}=${key}"
unset password key

bash scripts/backup.sh "$@"
