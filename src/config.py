"""Global UI and provider configuration."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

APP_NAME = "HoshiriPet"
CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"

PROVIDER_DEFAULTS = {
    "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "openai": {"base_url": "https://bobo-work.txlrai.cn/v1", "model": ""},
    "anthropic": {"base_url": "https://bobo-work.txlrai.cn", "model": ""},
}

DEFAULTS: dict[str, Any] = {
    "pos": None, "height": 300, "asset": "pet_edge_42", "particles": True,
    "chatter": True, "topmost": True, "opacity": 1.0,
    "provider": "deepseek",
    "provider_urls": {k: v["base_url"] for k, v in PROVIDER_DEFAULTS.items()},
    "provider_models": {k: v["model"] for k, v in PROVIDER_DEFAULTS.items()},
    # Legacy model setting remains accepted for existing DeepSeek installs.
    "model": "deepseek-chat",
}


def load() -> dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
    else:
        data = {}
    cfg = dict(DEFAULTS)
    cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
    cfg["provider"] = cfg["provider"] if cfg["provider"] in PROVIDER_DEFAULTS else "deepseek"
    urls = dict(DEFAULTS["provider_urls"])
    urls.update(data.get("provider_urls", {}) if isinstance(data.get("provider_urls"), dict) else {})
    models = dict(DEFAULTS["provider_models"])
    models.update(data.get("provider_models", {}) if isinstance(data.get("provider_models"), dict) else {})
    # Migrate the old single-model config into the default DeepSeek profile.
    if "provider_models" not in data and data.get("model"):
        models["deepseek"] = data["model"]
    cfg["provider_urls"], cfg["provider_models"] = urls, models
    cfg["model"] = models.get(cfg["provider"], "") or PROVIDER_DEFAULTS[cfg["provider"]]["model"]
    return cfg


def save(cfg: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")
