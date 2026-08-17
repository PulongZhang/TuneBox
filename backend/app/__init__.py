"""音乐播放器后端：FastAPI 应用工厂。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import routes
from .config import BACKEND_DIR, MUSIC_API, MUSIC_API_KEY, PROJECT_DIR


def _find_dist_dir() -> Path | None:
    """定位前端构建产物：开发结构 PROJECT_DIR/frontend/dist，容器扁平结构 BACKEND_DIR/frontend/dist。"""
    for base in (PROJECT_DIR, BACKEND_DIR):
        d = base / "frontend" / "dist"
        if d.is_dir():
            return d
    return None


def create_app() -> FastAPI:
    if not MUSIC_API or not MUSIC_API_KEY:
        raise RuntimeError(
            "未配置 MUSIC_API / MUSIC_API_KEY 环境变量，无法获取音源。"
            "请在 backend/.env 中填写（参考 backend/.env.example）。"
        )

    app = FastAPI(title="TuneBox Server", version="0.1.0")
    app.include_router(routes.router)

    # 生产形态：后端托管前端构建产物（开发时由 Vite 提供页面）
    dist_dir = _find_dist_dir()
    if dist_dir is not None:
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")

    return app


app = create_app()
