# TuneBox

自托管的网页音乐播放器：搜索、在线播放、同步歌词、下载音频/歌词、导入歌单。
数据源来自第三方音乐 API 中转（通过环境变量配置），不存储任何音乐文件。

## 技术栈

- 后端：FastAPI + uv（`backend/`），代理上游 API、流式转发音频（Range 支持）
- 前端：Vue 3 + TypeScript + Vite + Pinia + Element Plus（`frontend/`）
- 数据：播放列表/音量/模式保存在浏览器 localStorage，无数据库

## 环境要求

- uv（Python 包管理）
- Node.js 20+ 与 pnpm（仅开发前端时需要；生产模式用预构建产物）

## 配置

复制 `backend/.env.example` 为 `.env`（backend/ 或项目根目录均可），填写上游 API 地址：

```
MUSIC_API=https://your-api-host.example.com/api
```

> `MUSIC_API` 是必填项，缺失时服务拒绝启动。

## 开发模式

```bash
# 终端 1：后端（http://127.0.0.1:8901）
cd backend && uv run uvicorn app:app --port 8901

# 终端 2：前端（http://localhost:5273，/api 自动代理到后端）
cd frontend && pnpm install && pnpm dev
```

## 生产模式（单进程）

```bash
# 构建前端产物
cd frontend && pnpm install && pnpm build

# 启动（后端自动托管 frontend/dist，尝试 HTTPS 端口 443/2053/2087/8443）
cd backend && uv run music-server

# 指定端口 / 保存证书到 backend/ 目录
uv run music-server --port 2053 --save-cert
```

HTTPS 使用自签名证书，浏览器首次访问提示"证书不受信任"时选择"高级 → 继续访问"即可。

## 部署到 VPS（Docker）

需要一台 VPS（安装 Docker 与 Compose 插件，如 `curl -fsSL https://get.docker.com | sh`）。

### 镜像自动构建（GitHub Actions）

每次 push 到 `main`，GitHub Actions 自动构建镜像并推送到 **ghcr.io**（`ghcr.io/pulongzhang/tunebox:latest`，仓库 public 则镜像公开可匿名拉取）。工作流在 `.github/workflows/docker-image.yml`，无需额外配置 Token（使用 GITHUB_TOKEN，workflow 内已声明 `packages: write` 权限）。

### VPS 部署（拉镜像，无需构建）

```bash
# 1. 拉取代码（只需 compose 文件与 .env 示例）
git clone https://github.com/PulongZhang/TuneBox.git && cd TuneBox

# 2. 配置上游 API（必填）
cp backend/.env.example .env   # 编辑 .env 填写 MUSIC_API

# 3. 拉取镜像并启动
docker compose pull && docker compose up -d

# 4. 查看状态/日志
docker compose ps
docker compose logs -f
```

- 服务监听宿主机 `127.0.0.1:8000`，**不直接暴露公网**
- 公网访问两种方式：
  - 临时：宿主机上跑 `cloudflared tunnel --protocol http2 --url http://127.0.0.1:8000`
  - 固定域名（推荐）：配置命名隧道 `cloudflared tunnel run <tunnel>` 指向 `http://127.0.0.1:8000`
- 更新部署：`docker compose pull && docker compose up -d`

## 测试与检查

```bash
cd backend
uv run pytest        # 单元 + 路由测试
uv run ruff check app tests
```

## 主要功能

- 搜索歌曲（双击播放、单击加入列表、行内下载）
- 播放器：循环/随机/单曲模式、进度拖拽、音量、音质标签
- 同步歌词（含翻译），自动滚动高亮
- 导入歌单（歌单 ID 或链接），列表右键菜单
- 快捷键：空格（播放/暂停）、←/→（上/下曲）、↑/↓（音量）、M（静音）、Delete（移除当前）、Ctrl+S（下载音频）、Ctrl+L（下载歌词）
