"""统一处理「源码运行」与「PyInstaller 打包后」的资源路径。"""

from __future__ import annotations

import sys
from pathlib import Path


def _base() -> Path:
    if getattr(sys, "frozen", False):
        # onefile 是临时解包目录，onedir 是 exe 旁的 _internal
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


BASE = _base()
ASSETS = BASE / "assets" / "out"
SRC = BASE / "src"
