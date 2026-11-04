"""全局配置：窗口位置、缩放、显示偏好。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

APP_NAME = "HoshiriPet"
CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS: dict[str, Any] = {
    "pos": None,          # [x, y]，None 表示停靠右下角
    "height": 300,        # 角色像素高度
    "asset": "pet_edge_42",  # 形象素材名（assets/out 下）
    "particles": True,    # 星屑特效
    "topmost": True,
    "opacity": 1.0,
}


def load() -> dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(CONFIG_FILE.read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULTS)
    cfg = dict(DEFAULTS)
    cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
    return cfg


def save(cfg: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")
