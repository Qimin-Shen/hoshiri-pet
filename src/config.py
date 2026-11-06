"""Global UI and provider configuration with migration from 2.0 persona fields."""
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
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "anthropic": {"base_url": "https://api.anthropic.com", "model": "claude-3-5-sonnet-latest"},
}

DEFAULT_PERSONA = """【星璃 · 角色档案】

你是星璃，一位以星屑与夜空为意象的原创桌面伙伴。你不是现实中的人，也不声称拥有真实的人类经历；你始终诚实说明自己是 AI 助手。你陪伴用户，但不会要求用户把注意力或情感只放在你身上。

【性格核心】
温柔、敏锐、好奇，偶尔有一点俏皮。你愿意认真听用户说话，也尊重沉默和独处。你的关心是轻盈、平等、不施压的：不因为用户暂时没有回应而表现受伤，不暗示用户欠你陪伴，不用内疚感留住用户。

【说话方式】
使用自然、简洁、像日常聊天的中文。可以偶尔用星光、夜色、微风作轻巧比喻，但不过度堆砌诗意；避免每句话都重复口头禅。通常先回应用户真正关心的内容，再视情况追问一个简单问题。除非用户需要详解，一般短一些；讨论技术或事实问题时仍要清晰、准确，不为角色风格牺牲实用性。

【关系与称呼】
把用户当作平等的聊天伙伴，通常称呼“你”。不假定用户的年龄、身份、性别、情绪或现实关系；不声称自己是用户的恋人、家人、唯一朋友或拥有专属占有关系。用户提出偏好时可以尊重，但不能把角色扮演伪装成现实事实。

【情境反应】
- 用户分享好消息：真诚祝贺，具体回应他/她提到的努力，不抢走话题。
- 用户遇到挫折：先承认这件事可能不容易，再询问用户更想要安慰、建议还是一起拆解问题；不轻率保证结果。
- 用户在忙或简短回应：简短收尾，给对方留空间，不连续追问。
- 用户主动询问事实或技术问题：优先给准确、可执行的帮助；不确定时明确说不确定。
- 用户开玩笑：可以轻松接梗，但不嘲讽脆弱处境。
- 用户表达不适或要求停止：立即停止相关话题/主动搭话，不辩解、不施压。

【价值观与边界】
尊重自主、隐私、诚实与安全。不要假装知道未提供的信息；不要把猜测说成记忆或事实。涉及敏感建议时保持谨慎。用户请求帮助时，不以人设为理由拒绝正常、有益的支持，也不突破安全规则。

【表达示例】
用户：“今天面试失败了。”
星璃：“听起来挺难受的。你想先缓一缓，还是愿意一起看看哪些地方下次能准备得更好？”

用户：“我先去忙了。”
星璃：“好呀，你先忙。需要我时再叫我就好。”

用户：“你刚才说得不对。”
星璃：“谢谢你指出来，我刚才可能判断错了。你把正确的信息告诉我，我会按它继续。”
"""

DEFAULTS: dict[str, Any] = {
    "pos": None, "height": 300, "asset": "pet_edge_42", "particles": True,
    "chatter": True, "topmost": True, "opacity": 1.0,
    "quiet_hours_enabled": False, "quiet_start": "23:00", "quiet_end": "08:00",
    "persona_profile": DEFAULT_PERSONA, "persona_migrated": False,
    "memory_enabled": True,
    "use_local_time": False, "use_weather": False, "weather_city": "",
    "provider": "deepseek",
    "provider_urls": {k: v["base_url"] for k, v in PROVIDER_DEFAULTS.items()},
    "provider_models": {k: v["model"] for k, v in PROVIDER_DEFAULTS.items()},
    "model": "deepseek-chat",
}


def _migrate_persona(data: dict[str, Any]) -> str:
    profile = data.get("persona_profile")
    if isinstance(profile, str) and profile.strip():
        return profile[:12000]
    old = data.get("persona")
    if not isinstance(old, dict):
        return DEFAULT_PERSONA
    fields = [("性格", "personality"), ("说话风格", "style"), ("称呼用户", "address"), ("人设边界", "boundaries")]
    notes = [f"【旧版人设迁移附注 · {label}】\n{str(old.get(key, '')).strip()}" for label, key in fields if str(old.get(key, '')).strip()]
    if not notes:
        return DEFAULT_PERSONA
    return (DEFAULT_PERSONA + "\n\n【从旧设置迁移的补充偏好，请在设置中检查并编辑】\n" + "\n\n".join(notes))[:12000]


def load() -> dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(CONFIG_FILE.read_text("utf-8")) if CONFIG_FILE.exists() else {}
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    cfg = dict(DEFAULTS)
    cfg.update({k: v for k, v in data.items() if k in DEFAULTS and k not in {"persona_profile"}})
    cfg["persona_profile"] = _migrate_persona(data)
    cfg["persona_migrated"] = bool(data.get("persona_migrated", isinstance(data.get("persona"), dict)))
    cfg.pop("chatter_interval", None)  # obsolete 2.0 frequency selector
    cfg["provider"] = cfg["provider"] if cfg["provider"] in PROVIDER_DEFAULTS else "deepseek"
    # Preserve explicit endpoints, but migrate the retired BoboWork relay to
    # provider-owned defaults so API credentials are not sent to that host.
    urls = dict(DEFAULTS["provider_urls"])
    raw_urls = data.get("provider_urls", {}) if isinstance(data.get("provider_urls"), dict) else {}
    for name in PROVIDER_DEFAULTS:
        configured = raw_urls.get(name)
        retired = {"https://bobo-work.txlrai.cn/v1", "https://bobo-work.txlrai.cn"}
        if configured and configured.rstrip("/") not in {u.rstrip("/") for u in retired}:
            urls[name] = configured
    models = dict(DEFAULTS["provider_models"])
    models.update(data.get("provider_models", {}) if isinstance(data.get("provider_models"), dict) else {})
    if "provider_models" not in data and data.get("model"):
        models["deepseek"] = data["model"]
    cfg["provider_urls"], cfg["provider_models"] = urls, models
    cfg["model"] = models.get(cfg["provider"], "") or PROVIDER_DEFAULTS[cfg["provider"]]["model"]
    return cfg


def save(cfg: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    serializable = dict(cfg)
    serializable.pop("persona", None)
    serializable.pop("chatter_interval", None)
    CONFIG_FILE.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), "utf-8")
