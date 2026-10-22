# syntax=docker/dockerfile:1
# Ảnh backend HỏiCon (spec 012). Build context là GỐC repo (xem infra/compose.prod.yml):
#   docker build -f backend/Dockerfile .
# Bố cục trong ảnh giữ y như repo (/app/backend, /app/data, /app/docs/schemas) vì mã tìm `data/drills` và
# `docs/schemas/drill_script.v1.json` theo đường dẫn tương đối với mã nguồn (domain/drill.py).

FROM ghcr.io/astral-sh/uv:0.13.0 AS uv

FROM python:3.12-slim-bookworm AS build
COPY --from=uv /uv /bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT=/app/backend/.venv
WORKDIR /app/backend
# Lớp phụ thuộc trước (đổi mã nguồn không phải tải lại). `--frozen`: đúng uv.lock, không tự giải lại.
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
COPY backend/src ./src
COPY data/case_file /app/data/case_file
COPY data/coach /app/data/coach
COPY data/drills /app/data/drills
COPY data/scenarios /app/data/scenarios
COPY data/threat_seed.demo.json /app/data/threat_seed.demo.json
COPY backend/eval/baseline*.json /app/backend/eval/
COPY docs/schemas /app/docs/schemas
RUN uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm AS runtime
ENV PATH=/app/backend/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
# Người dùng không đặc quyền; mã nguồn thuộc root và chỉ đọc với tiến trình (ghi đè mã khi bị tấn công khó hơn).
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin hoicon
COPY --from=build /app /app
WORKDIR /app/backend
USER 10001
EXPOSE 18000
# --proxy-headers: IP khách thật từ X-Forwarded-For của Caddy (giới hạn tần suất ghép đôi theo nguồn, pairing.py).
# `*` chấp nhận được vì cổng 18000 KHÔNG xuất ra ngoài và chỉ Caddy nằm cùng mạng `api` với backend (web ở mạng riêng).
CMD ["uvicorn", "hoicon.api.main:app", "--host", "0.0.0.0", "--port", "18000", \
     "--proxy-headers", "--forwarded-allow-ips", "*", "--timeout-graceful-shutdown", "20"]
