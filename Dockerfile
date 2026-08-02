# syntax=docker/dockerfile:1

# ---------- 阶段 1：构建前端 ----------
FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY frontend/ .
RUN pnpm build

# ---------- 阶段 2：运行时（后端 + 前端产物） ----------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime
WORKDIR /app

# 后端依赖（uv.lock 在仓库根，workspace 锁文件）
COPY backend/pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 后端代码 + 前端构建产物
COPY backend/app ./app
COPY --from=frontend-build /build/dist ./frontend/dist

# MUSIC_API 由 docker compose 的 env_file: .env 在运行时注入
# （容器内 config.py 从环境变量读取，无需构建时预设）

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
