"""DeepSeek API 客户端：流式对话 + 余额查询。"""

from __future__ import annotations

import json
from typing import Iterator

import httpx

BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
TIMEOUT = httpx.Timeout(connect=10.0, read=180.0, write=30.0, pool=10.0)

SYSTEM_PROMPT = (
    "你是「星璃」（Hoshiri），一位住在用户桌面右下角的少女。"
    "你性格温柔、带一点俏皮，说话简短自然，像朋友聊天，不要长篇大论。"
    "你称呼用户为「你」。回答一般控制在 80 字以内，除非用户明确要求详细解释。"
    "当用户问技术问题时，可以正常给方案，但仍保持简洁。"
)


class DeepSeekError(RuntimeError):
    pass


def _headers(key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def balance(key: str) -> dict:
    """返回 {is_available, currency, total, granted, topped_up}。"""
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.get(f"{BASE_URL}/user/balance", headers=_headers(key))
    if resp.status_code == 401:
        raise DeepSeekError("API Key 无效")
    if resp.status_code != 200:
        raise DeepSeekError(f"余额查询失败 HTTP {resp.status_code}")

    data = resp.json()
    infos = data.get("balance_infos") or []
    info = infos[0] if infos else {}
    return {
        "is_available": bool(data.get("is_available")),
        "currency": info.get("currency", "CNY"),
        "total": float(info.get("total_balance", 0) or 0),
        "granted": float(info.get("granted_balance", 0) or 0),
        "topped_up": float(info.get("topped_up_balance", 0) or 0),
    }


def stream_chat(
    key: str,
    messages: list[dict],
    model: str = DEFAULT_MODEL,
) -> Iterator[tuple[str, dict | None]]:
    """逐块产出 (文本, usage)。最后一块的 usage 非空。"""
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 1.1,
    }

    usage: dict | None = None
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            with client.stream(
                "POST", f"{BASE_URL}/chat/completions", headers=_headers(key), json=payload
            ) as resp:
                if resp.status_code == 401:
                    raise DeepSeekError("API Key 无效")
                if resp.status_code == 402:
                    raise DeepSeekError("账户余额不足")
                if resp.status_code != 200:
                    body = resp.read().decode("utf-8", "ignore")[:300]
                    raise DeepSeekError(f"HTTP {resp.status_code}: {body}")

                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        obj = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue

                    if obj.get("usage"):
                        usage = obj["usage"]

                    for choice in obj.get("choices") or []:
                        text = (choice.get("delta") or {}).get("content") or ""
                        if text:
                            yield text, None
    except httpx.RequestError as exc:
        raise DeepSeekError(f"网络错误：{exc.__class__.__name__}") from exc

    yield "", usage
