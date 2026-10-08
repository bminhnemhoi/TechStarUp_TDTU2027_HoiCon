#!/usr/bin/env bash
# Dừng (KHÔNG xóa) các container Docker không thuộc HỏiCon để giải phóng RAM cho máy ảo Android / Gradle.
#   bash scripts/stop-other-stacks.sh          # liệt kê rồi hỏi xác nhận
#   bash scripts/stop-other-stacks.sh --yes    # không hỏi (Claude chỉ chạy khi Minh đồng ý — quyền "ask")
# Bật lại: docker start <tên> (hoặc docker compose up -d trong dự án tương ứng). Dữ liệu volume được giữ nguyên.
set -euo pipefail

mapfile -t OTHERS < <(docker ps --format '{{.Names}}' | grep -v '^hoicon-' || true)
if [ "${#OTHERS[@]}" -eq 0 ]; then
  echo "Không có container nào ngoài HỏiCon đang chạy."
  exit 0
fi

echo "Container đang chạy không thuộc HỏiCon (${#OTHERS[@]}):"
docker ps --filter "name=^($(IFS='|'; echo "${OTHERS[*]}"))$" --format '  {{.Names}}\t{{.Image}}\t{{.Status}}'
docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' "${OTHERS[@]}" 2>/dev/null | sed 's/^/  RAM: /' || true

if [ "${1:-}" != "--yes" ]; then
  read -r -p "Dừng tất cả các container trên? [y/N] " ans
  [[ "$ans" =~ ^[yY]$ ]] || { echo "Hủy."; exit 0; }
fi

printf '%s\n' "${OTHERS[@]}" >"${TMPDIR:-/tmp}/hoicon-stopped-stacks.txt"
docker stop "${OTHERS[@]}" >/dev/null
echo "Đã dừng ${#OTHERS[@]} container. Danh sách lưu ở ${TMPDIR:-/tmp}/hoicon-stopped-stacks.txt"
echo "Bật lại: xargs docker start < ${TMPDIR:-/tmp}/hoicon-stopped-stacks.txt"
