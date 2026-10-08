#!/usr/bin/env bash
# Sinh client TypeScript cho web từ OpenAPI của FastAPI (luật "hợp đồng trước" — CLAUDE.md #10).
#   bash scripts/gen-api-client.sh      (hoặc: pnpm gen:api)
# Không cần API đang chạy: lấy schema trực tiếp từ app.openapi().
set -euo pipefail
cd "$(dirname "$0")/.."

OUT_DIR=apps/web/src/lib/api
mkdir -p "$OUT_DIR"

uv run --directory backend python -c "import json; from hoicon.api.main import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=1))" \
  >"$OUT_DIR/openapi.json"
pnpm --dir apps/web exec openapi-typescript src/lib/api/openapi.json -o src/lib/api/schema.d.ts

echo "Đã sinh $OUT_DIR/schema.d.ts — commit cùng thay đổi API."
