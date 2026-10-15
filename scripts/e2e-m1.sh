#!/usr/bin/env bash
# scripts/e2e-m1.sh — Kiểm chứng Gate M1 phần MÁY CHỦ (spec 023, P2-07, SC-006). Cần Postgres dev (cổng 15432).
#
# Mọi bước đều CHẠY kiểm tra thật; bước nào chưa tự động được thì in rõ "CHƯA TỰ ĐỘNG", không tính là đạt.
# 1. check-spec-trace          2. hợp đồng schema (action_view, incident_decision)     3. ruff check + format
# 4. luồng máy chủ trên Postgres thật: POST /v1/events → job notify_guardian → gửi (Zalo MOCK) → /a/[token] → quyết
#    định → sự cố đóng; token chỉ lưu SHA-256, không nằm trong jobs/log; 0 số điện thoại thô (test_guardian_alert.py …)
# 5. quét số điện thoại thô trong mã nguồn + gitleaks trên cây làm việc (kể cả tệp chưa commit)
# 6. chặng Android ↔ máy chủ (máy ảo gửi sự kiện thật, SafePause ≤ 3 s) — CHƯA TỰ ĐỘNG, xem specs/023-…/evidence.md
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
step() { echo -e "\n${YELLOW}[$1/6] $2${NC}"; }
ok() { echo -e "${GREEN}✓ $1${NC}"; }

step 1 "Truy vết đặc tả (scripts/check-spec-trace.py)"
python3 scripts/check-spec-trace.py
ok "check-spec-trace đạt"

step 2 "Hợp đồng schema spec 023"
uv run --directory backend pytest -p no:cacheprovider -q tests/contract/test_action_schemas.py
ok "fixture hợp lệ/không hợp lệ đúng như mong đợi"

step 3 "ruff check + format (backend)"
uv run --directory backend ruff check --no-cache .
uv run --directory backend ruff format --no-cache --check .
ok "ruff sạch"

step 4 "Luồng máy chủ M1 trên Postgres thật (Zalo MOCK, trong tiến trình)"
uv run --directory backend pytest -p no:cacheprovider -q -s -W ignore \
  tests/integration/test_guardian_alert.py tests/integration/test_action_token_service.py \
  tests/unit/test_action_token_log.py \
  || { echo -e "${RED}✗ luồng máy chủ chưa đạt (Postgres 15432 có chạy không?)${NC}"; exit 1; }
ok "sự kiện → cảnh báo → quyết định → đóng sự cố; token không lộ (số ms ở dòng 'M1 máy chủ' phía trên)"

step 5 "Quyền riêng tư: số điện thoại thô trong mã nguồn + gitleaks"
RAW_PHONE='(\+84|0)(3[2-9]|5[689]|7[06-9]|8[1-689]|9[0-46-9])[0-9]{7}'
if grep -rEn "$RAW_PHONE" backend/src apps/web/src; then
  echo -e "${RED}✗ có chuỗi giống số điện thoại thô trong mã nguồn${NC}"
  exit 1
fi
for path in backend/src backend/tests apps/web/src docs/schemas scripts specs/023-guardian-alert; do
  gitleaks dir --config .gitleaks.toml --redact --no-banner --log-level warn "$path"
done
ok "không có số điện thoại thô; gitleaks sạch"

step 6 "Chặng Android ↔ máy chủ (máy ảo)"
echo -e "${YELLOW}! CHƯA TỰ ĐỘNG: app Lính gác chưa được nối với API dev trong kịch bản này. Số SafePause hiện có là của${NC}"
echo -e "${YELLOW}  spec 001/022 trên máy ảo (không phải máy thật). Không tính bước này là đạt.${NC}"

echo -e "\n${GREEN}Gate M1 phần máy chủ: 5/5 bước tự động ĐẠT · bước 6 (Android ↔ máy chủ) còn mở.${NC}"
