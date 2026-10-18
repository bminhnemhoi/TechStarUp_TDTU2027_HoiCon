#!/usr/bin/env bash
# Hàm dùng chung cho scripts/deploy-vps.sh và scripts/backup-vps.sh: đọc tệp biến PROD mà KHÔNG `source` nó (không thi
# hành gì) và không bao giờ in giá trị. Cần biến ENV_FILE đã đặt. File này chỉ được `source`, không chạy trực tiếp.

# Quyền tệp biến phải là 600/400 (chỉ chủ đọc được); ngược lại in lỗi ra stderr và trả mã khác 0.
envfile_check_mode() {
  local mode
  mode=$(stat -c '%a' "$ENV_FILE")
  case "$mode" in
    600 | 400) return 0 ;;
    *)
      echo "LỖI: $ENV_FILE có quyền $mode: phải là 600 (chạy: chmod 600 $ENV_FILE)" >&2
      return 1
      ;;
  esac
}

# get <TÊN>: in giá trị của TÊN (rỗng nếu không có); bỏ \r và cặp nháy ngoài cùng.
get() {
  local v
  v=$(grep -m1 -E "^$1=" "$ENV_FILE" | cut -d= -f2- || true)
  v=${v%$'\r'}
  v=${v#\"}; v=${v%\"}
  v=${v#\'}; v=${v%\'}
  printf '%s' "$v"
}
