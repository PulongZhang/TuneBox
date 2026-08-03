"""应用配置：从环境变量读取（支持项目根目录与 backend/ 下的 .env）。"""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


def _load_env_file(path: Path) -> None:
    """加载 .env（KV 格式），不覆盖已存在的环境变量。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


_load_env_file(PROJECT_DIR / ".env")
_load_env_file(BACKEND_DIR / ".env")

# 上游音乐 API 中转地址（必填），形如 https://example.com/api
MUSIC_API = os.environ.get("MUSIC_API", "").rstrip("/")
