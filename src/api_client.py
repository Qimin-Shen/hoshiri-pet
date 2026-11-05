"""Protocol adapters for DeepSeek, OpenAI-compatible and Anthropic APIs."""
from __future__ import annotations

import json
from typing import Iterator
from urllib.parse import urlparse

import httpx

TIMEOUT = httpx.Timeout(connect=10.0, read=180.0, write=30.0, pool=10.0)
DEFAULT_URLS = {
    "deepseek": "https://api.deepseek.com",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
}
SYSTEM_PROMPT = (
    "你是「星璃」（Hoshiri），一位住在用户桌面右下角的少女。"
    "你性格温柔、带一点俏皮，说话简短自然，像朋友聊天，不要长篇大论。"
    "你称呼用户为「你」。回答一般控制在 80 字以内，除非用户明确要求详细解释。"
    "当用户问技术问题时，可以正常给方案，但仍保持简洁。"
)


class APIError(RuntimeError):
    pass


def _base(provider: str, base_url: str | None) -> str:
    value = (base_url or DEFAULT_URLS.get(provider, "")).strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise APIError("Base URL 必须是有效的 http/https 地址")
    return value


def _error(resp: httpx.Response) -> APIError:
    body = resp.read().decode("utf-8", "replace")[:500]
    return APIError(f"HTTP {resp.status_code}: {body or resp.reason_phrase}")


def _openai_headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "text/event-stream"}


def _anthropic_headers(key: str) -> dict[str, str]:
    return {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json", "Accept": "text/event-stream"}


def test_connection(provider: str, base_url: str, key: str, model: str) -> str:
    """Send a small provider-appropriate validation request (may consume a token)."""
    if not key.strip():
        raise APIError("请先填写 API Key")
    if not model.strip():
        raise APIError("请填写服务商提供给你的模型名称")
    base = _base(provider, base_url)
    if provider == "deepseek":
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(f"{base}/user/balance", headers={"Authorization": f"Bearer {key}"})
        if resp.status_code != 200:
            raise _error(resp)
        return "连接成功（DeepSeek 余额接口）"
    if provider == "openai":
        payload = {"model": model, "messages": [{"role": "user", "content": "Reply with OK"}], "max_tokens": 1}
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(f"{base}/chat/completions", headers=_openai_headers(key), json=payload)
        if resp.status_code != 200:
            raise _error(resp)
        return "连接成功（OpenAI Chat Completions）"
    if provider == "anthropic":
        payload = {"model": model, "max_tokens": 1, "messages": [{"role": "user", "content": "Reply with OK"}]}
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(f"{base}/v1/messages", headers=_anthropic_headers(key), json=payload)
        if resp.status_code != 200:
            raise _error(resp)
        return "连接成功（Anthropic Messages）"
    raise APIError("不支持的服务商")


def stream_chat(provider: str, base_url: str, key: str, messages: list[dict], model: str) -> Iterator[tuple[str, dict | None]]:
    if not key.strip():
        raise APIError("未配置此服务商的 API Key")
    if not model.strip():
        raise APIError("请先在设置中填写模型名称")
    base = _base(provider, base_url)
    if provider in ("deepseek", "openai"):
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": 1.1,
        }
        with httpx.Client(timeout=TIMEOUT) as client:
            with client.stream("POST", f"{base}/chat/completions", headers=_openai_headers(key), json=payload) as resp:
                if resp.status_code != 200:
                    raise _error(resp)
                usage = None
                for line in resp.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        obj = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    if obj.get("usage"):
                        u = obj["usage"]
                        usage = {"prompt_tokens": u.get("prompt_tokens", 0), "completion_tokens": u.get("completion_tokens", 0)}
                    for choice in obj.get("choices") or []:
                        text = (choice.get("delta") or {}).get("content") or ""
                        if text:
                            yield text, None
                yield "", usage
        return
    if provider == "anthropic":
        payload = {"model": model, "system": SYSTEM_PROMPT, "max_tokens": 2048, "messages": messages, "stream": True, "temperature": 1.1}
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        with httpx.Client(timeout=TIMEOUT) as client:
            with client.stream("POST", f"{base}/v1/messages", headers=_anthropic_headers(key), json=payload) as resp:
                if resp.status_code != 200:
                    raise _error(resp)
                event = ""
                for line in resp.iter_lines():
                    if line.startswith("event:"):
                        event = line[6:].strip()
                    elif line.startswith("data:"):
                        try:
                            obj = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            continue
                        kind = obj.get("type", event)
                        if kind == "message_start":
                            usage["prompt_tokens"] = (obj.get("message", {}).get("usage") or {}).get("input_tokens", 0)
                        elif kind == "content_block_delta" and (obj.get("delta") or {}).get("type") == "text_delta":
                            text = obj["delta"].get("text", "")
                            if text:
                                yield text, None
                        elif kind == "message_delta":
                            usage["completion_tokens"] = (obj.get("usage") or {}).get("output_tokens", 0)
                        elif kind == "error":
                            raise APIError(str(obj.get("error", {}).get("message", "Anthropic stream error")))
                yield "", usage
        return
    raise APIError("不支持的服务商")


def balance(key: str, base_url: str | None = None) -> dict:
    """DeepSeek proprietary balance endpoint; no gateway balance is assumed."""
    base = _base("deepseek", base_url)
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.get(f"{base}/user/balance", headers={"Authorization": f"Bearer {key}"})
    if resp.status_code != 200:
        raise _error(resp)
    data = resp.json()
    info = (data.get("balance_infos") or [{}])[0]
    return {"is_available": bool(data.get("is_available")), "currency": info.get("currency", "CNY"), "total": float(info.get("total_balance", 0) or 0), "granted": float(info.get("granted_balance", 0) or 0), "topped_up": float(info.get("topped_up_balance", 0) or 0)}
