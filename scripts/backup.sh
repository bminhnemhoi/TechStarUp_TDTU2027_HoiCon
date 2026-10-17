#!/usr/bin/env bash
# Sao lưu mã hóa Postgres của HỏiCon (spec 034). Chạy từ thư mục gốc repo:
#   bash scripts/backup.sh               # sao lưu + xoay vòng (giữ 7 bản ngày + 4 bản tuần)
#   bash scripts/backup.sh restore-check # khôi phục bản mới nhất vào DB tạm hoicon_restore_check rồi kiểm
# Cần: docker (container Postgres, tên trong HOICON_BACKUP_CONTAINER), HOICON_BACKUP_KEY_<kid> trong backend/.env.
# Lịch chạy (cron/systemd timer) và nơi lưu ngoài máy thuộc spec 012; xem docs/setup/BACKUP.md.
set -euo pipefail
cd "$(dirname "$0")/.."

run() { uv run --directory backend python -m hoicon.ops.backup "$@"; }

case "${1:-backup}" in
  backup)
    run backup
    run rotate
    ;;
  restore-check)
    run restore-check
    ;;
  rotate)
    run rotate "${@:2}"
    ;;
  *)
    echo "Dùng: scripts/backup.sh [backup|restore-check|rotate [--dry-run]]" >&2
    exit 2
    ;;
esac
