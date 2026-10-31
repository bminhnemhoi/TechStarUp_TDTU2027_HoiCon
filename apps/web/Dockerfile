# syntax=docker/dockerfile:1
# Ảnh web người giám hộ HỏiCon (Next.js, spec 012). Build context là GỐC repo (pnpm workspace + pnpm-lock.yaml):
#   docker build -f apps/web/Dockerfile .
FROM node:22.23.3-bookworm-slim
ENV NEXT_TELEMETRY_DISABLED=1 CI=true
RUN corepack enable
WORKDIR /app
# Lớp phụ thuộc trước; `--filter` chỉ cài gói web (không kéo `concurrently` của gốc repo).
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/
RUN pnpm install --frozen-lockfile --filter @hoicon/web
COPY apps/web apps/web
# Rewrite `/v1/*` của Next cố định lúc build (next.config.ts). Ở prod Caddy đưa `/v1/*` thẳng tới API nên đường này chỉ là
# dự phòng (khi chạy web riêng không qua Caddy).
ARG HOICON_API_URL=http://backend:18000
ENV HOICON_API_URL=$HOICON_API_URL
RUN pnpm --dir apps/web build && chown -R node:node /app/apps/web/.next
USER node
WORKDIR /app/apps/web
EXPOSE 3100
CMD ["node_modules/.bin/next", "start", "-p", "3100", "-H", "0.0.0.0"]
