# HỏiCon web (`@hoicon/web`)

Next.js 16 (App Router) + Tailwind v4, cổng **3100**. Trang dự kiến: `docs/ARCHITECTURE.md` §5. Next 16 có thay đổi phá
vỡ — đọc `AGENTS.md` (tài liệu kèm trong `node_modules/next/dist/docs/`) trước khi viết code.

```bash
pnpm install                    # ở gốc repo (pnpm workspace)
pnpm --dir apps/web dev         # http://localhost:3100
pnpm --dir apps/web typecheck   # next typegen && tsc --noEmit
pnpm --dir apps/web lint
pnpm gen:api                    # sinh src/lib/api/schema.d.ts từ OpenAPI của backend
```

## Kiểm thử E2E (Playwright, spec 027)

Chạy trên bản **đã build** (`next start` cổng 3100). Mặc định mạng được chặn bằng fixture hợp đồng trong
`docs/schemas/fixtures/` nên không cần API hay DB:

```bash
pnpm --dir apps/web build
pnpm --dir apps/web exec playwright install chromium   # một lần
pnpm --dir apps/web e2e                                # login · incidents · detail · a11y (axe, 3 kích thước, chữ 200%)
pnpm --dir apps/web e2e a11y                           # chụp ảnh vào ~/hoicon-evidence/027-guardian-web/
```

Kịch bản **live** (`e2e/live.spec.ts`) chạy với API + DB dev thật và tự bỏ qua nếu thiếu `HOICON_E2E_LIVE=1`. Rewrite
`/v1/*` của Next được cố định lúc build, nên build trỏ vào đúng API (cổng 18000 mặc định hoặc `HOICON_API_URL`):

```bash
# 1) API với khóa JWT ngẫu nhiên dùng một lần (≥ 32 ký tự), ví dụ cổng 18010
uv run --directory backend uvicorn hoicon.api.main:app --port 18010 --loop asyncio:SelectorEventLoop
# 2) web build trỏ vào API đó, rồi chạy
HOICON_API_URL=http://127.0.0.1:18010 pnpm --dir apps/web build
HOICON_E2E_LIVE=1 pnpm --dir apps/web e2e live
```

Dữ liệu live là gia đình demo "E2E 027" do `python -m hoicon.ops.guardian_link` dựng và dọn (chỉ chạy khi `HOICON_ENV=dev`).

Token màu/font tạm ở `src/app/globals.css` — thay bằng `design-system/hoicon/tokens.json` ở P1-05
(`docs/DESIGN-SYSTEM.md` thắng mọi gợi ý plugin). Font Be Vietnam Pro qua `next/font/google`.
