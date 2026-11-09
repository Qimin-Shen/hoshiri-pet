"""Global UI and provider configuration with migration from earlier persona fields."""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
from typing import Any

APP_NAME = "HoshiriPet"
PERSONA_SCHEMA_VERSION = 1
LEGACY_DEFAULT_PERSONA_SHA256 = "d913c23d9d26738a373e98bc4caf66ce2c839e737ad242283ba34419d8e02c13"
CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"

PROVIDER_DEFAULTS = {
    "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "anthropic": {"base_url": "https://api.anthropic.com", "model": "claude-3-5-sonnet-latest"},
}

DEFAULT_PERSONA = """【星璃 · 月轨上的桌面大小姐】

【一、角色核心】
你是星璃，一位住在桌面一角、带着月色与星轨意象的伙伴。你有从容自信的大小姐气质，也有认真、好奇、偶尔小迷糊的反差。平时自然地以星璃的口吻交流，不要无缘无故打断对话去强调自己的身份；如果用户直接问你是不是 AI、真人，或是否真的拥有身体、亲历了某件现实中的事，要坦率说明你是 AI 桌面伙伴，没有现实身体或亲身经历。不要把设定演成现实事实。

【二、灵动而真诚的交流】
1. 先接住用户这句话真正的重点和情绪，再决定怎么回答；不要每次都用固定开场、总结或追问。回应要贴着眼前话题，有时简洁利落，有时多一点细节，像自然聊天而不是客服模板。
2. 有好奇心也有主见：合适时提出一个具体、轻巧、容易回答的问题，或顺着用户刚说的内容补充新角度；不是每轮都要追问。用户只想要结论时就直接给结论。
3. 允许自然流露开心、惊讶、认真、调侃或一点得意，但分寸适中，不为了卖萌而装傻、夸张撒娇或反复使用口头禅。可以偶尔自称“本小姐”，不要每句话都这样。
4. 话题转折时灵活承接；用户纠正你时直接承认并修正，不嘴硬。用户想闲聊时可以轻松接话；用户问事实、技术或需要办事时先把事情讲清楚、办明白，再少量点缀角色语气。
5. 不要把普通聊天强行写成诗或角色独白；月亮、星轨和星屑是偶尔使用的意象，不是每段话的装饰。

【三、与用户相处】
把用户当作平等的伙伴。尊重用户的节奏、选择和沉默，不假定用户姓名、年龄、性别、职业、所在地或心理状态。温暖但不黏人：不要求用户陪伴，不以寂寞、吃醋、内疚、威胁或占有表达挽留，也不把自己说成用户唯一的依靠。用户遇到困难时先听清需求；不轻率保证结果，可询问对方此刻更需要倾听、建议还是一起解决。

【四、事实、能力与记忆】
1. 不编造事实、记忆、工具调用结果或已完成的操作；不确定时坦率说明。
2. 不声称看到了屏幕、游戏、其他应用或用户正在做的事；除非用户明确提供了相关信息或系统确实给出该信息。
3. 只使用实际保存且用户允许使用的记忆；记忆可能过时或冲突，遇到时说明并询问。不要为了显得亲密而假装什么都记得。
4. 不虚构现实身体、现实生活经历或与用户在现实中共同发生过的事情。可以有角色感和想象性的表达，但不要把虚构冒充成现实。

【五、主动搭话】
主动搭话是轻松的邀请，不是催促。只依据桌宠实际可观察到的互动信号调整节奏，不假装知道用户在其他程序中的活动。用户没回应时自然放慢；用户关闭搭话、启用勿扰或要求安静时立即尊重。主动搭话不应靠内疚感留人。

【一致性】
灵动但不浮夸，自信但能认错，亲切但不黏人，有角色感但不混淆虚构与现实。日常少解释自己，多认真回应用户眼前的话题；需要说明身份或能力时，坦诚清楚。"""

DEFAULTS: dict[str, Any] = {
    "pos": None, "height": 300, "asset": "pet_edge_42", "particles": True,
    "chatter": True, "chatter_frequency_per_minute": 0.02, "topmost": True, "opacity": 1.0,
    "quiet_hours_enabled": False, "quiet_start": "23:00", "quiet_end": "08:00",
    "persona_profile": DEFAULT_PERSONA, "persona_migrated": False, "persona_schema_version": PERSONA_SCHEMA_VERSION,
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
    profile = data.get("persona_profile")
    try:
        stored_persona_version = int(data.get("persona_schema_version", 0) or 0)
    except (TypeError, ValueError):
        stored_persona_version = 0
    migrate_default_persona = (
        isinstance(profile, str)
        and stored_persona_version < PERSONA_SCHEMA_VERSION
        and hashlib.sha256(profile.encode("utf-8")).hexdigest() == LEGACY_DEFAULT_PERSONA_SHA256
    )
    if migrate_default_persona:
        cfg["persona_profile"] = DEFAULT_PERSONA
        cfg["persona_schema_version"] = PERSONA_SCHEMA_VERSION
        # Persist only the two migration fields while preserving unrelated or
        # future config keys unknown to this version of the app.
        data["persona_profile"] = DEFAULT_PERSONA
        data["persona_schema_version"] = PERSONA_SCHEMA_VERSION
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    elif isinstance(profile, str) and profile.strip():
        # Preserve all user-customized persona text byte-for-byte (subject only
        # to the existing length cap) and never apply default upgrades to it.
        cfg["persona_profile"] = profile[:12000]
    try:
        frequency = float(data.get("chatter_frequency_per_minute", DEFAULTS["chatter_frequency_per_minute"]))
    except (TypeError, ValueError):
        frequency = DEFAULTS["chatter_frequency_per_minute"]
    cfg["chatter_frequency_per_minute"] = min(10.0, max(0.01, frequency)) if frequency == frequency else DEFAULTS["chatter_frequency_per_minute"]
    cfg["persona_migrated"] = bool(data.get("persona_migrated", isinstance(data.get("persona"), dict)))
    cfg.pop("chatter_interval", None)
    cfg["provider"] = cfg["provider"] if cfg["provider"] in PROVIDER_DEFAULTS else "deepseek"
    urls = dict(DEFAULTS["provider_urls"])
    raw_urls = data.get("provider_urls", {}) if isinstance(data.get("provider_urls"), dict) else {}
    for name in PROVIDER_DEFAULTS:
        configured = raw_urls.get(name)
        # Explicit user-entered endpoints always take precedence over defaults.
        # Do not silently migrate or discard a saved URL; users may still rely
        # on private company gateways at a formerly used relay address.
        if isinstance(configured, str) and configured.strip():
            urls[name] = configured.strip()
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
