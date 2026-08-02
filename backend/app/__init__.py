"""音乐播放器后端：FastAPI 应用工厂。"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import routes
from .config import MUSIC_API, PROJECT_DIR


def create_app() -> FastAPI:
    if not MUSIC_API:
        raise RuntimeError(
            "未配置 MUSIC_API 环境变量，无法获取音源。"
            "请在 backend/.env 中填写（参考 backend/.env.example）。"
        )

    app = FastAPI(title="Music Server", version="0.1.0")
    app.include_router(routes.router)

    # 生产形态：后端托管前端构建产物（开发时由 Vite 提供页面）
    dist_dir = PROJECT_DIR / "frontend" / "dist"
    if dist_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")

    return app


app = create_app()
