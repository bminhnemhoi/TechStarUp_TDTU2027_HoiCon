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

Token màu/font tạm ở `src/app/globals.css` — thay bằng `design-system/hoicon/tokens.json` ở P1-05
(`docs/DESIGN-SYSTEM.md` thắng mọi gợi ý plugin). Font Be Vietnam Pro qua `next/font/google`.
