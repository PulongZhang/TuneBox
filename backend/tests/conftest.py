"""pytest 全局配置：测试环境变量需在 import app 之前设置。"""

import os

os.environ.setdefault("MUSIC_API", "https://test-upstream.example.com/api")
