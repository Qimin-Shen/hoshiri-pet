from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import api_client
import config
import keystore
import httpx

_REAL_CLIENT = httpx.Client


class ApiClientTests(unittest.TestCase):
    def call_with_response(self, handler, fn):
        transport = httpx.MockTransport(handler)

        def client_factory(*args, **kwargs):
            return _REAL_CLIENT(transport=transport, timeout=kwargs.get("timeout"))

        with patch.object(api_client.httpx, "Client", side_effect=client_factory):
            result = fn()
            if hasattr(result, "__next__"):
                return list(result)
            return result

    def test_system_prompt_encourages_lively_chat_without_unprompted_ai_disclosure(self):
        prompt = api_client.build_system_prompt("你是星璃，轻快、好奇，回应自然。")
        self.assertIn("日常交流无需主动声明自己是 AI", prompt)
        self.assertIn("直接询问", prompt)
        self.assertIn("必须如实说明你是 AI 桌面伙伴", prompt)
        self.assertIn("自然灵动", prompt)
        self.assertIn("轻快、好奇", prompt)
        self.assertNotIn("诚实说明自己为 AI", prompt)

    def test_system_prompt_keeps_capability_and_dependency_boundaries(self):
        prompt = api_client.build_system_prompt("角色设定")
        self.assertIn("不得谎称真人", prompt)
        self.assertIn("不得假装看见屏幕", prompt)
        self.assertIn("不得以制造内疚、嫉妒、占有或依赖的方式留住用户", prompt)
        self.assertIn("【原创角色档案】", prompt)
        self.assertIn("角色设定", prompt)

    def test_openai_stream_path_headers_and_usage(self):
        seen = {}

        def handler(request):
            seen["url"] = str(request.url)
            seen["authorization"] = request.headers.get("authorization")
            seen["json"] = json.loads(request.content)
            return httpx.Response(200, text=(
                'data: {"choices":[{"delta":{"content":"hi"}}]}\n\n'
                'data: {"choices":[],"usage":{"prompt_tokens":3,"completion_tokens":2}}\n\n'
                'data: [DONE]\n\n'
            ), headers={"content-type": "text/event-stream"})

        chunks = list(self.call_with_response(handler, lambda: api_client.stream_chat(
            "openai", "https://api.example.com/v1", "secret", [{"role": "user", "content": "x"}], "org-model"
        )))
        self.assertEqual(seen["url"], "https://api.example.com/v1/chat/completions")
        self.assertEqual(seen["authorization"], "Bearer secret")
        self.assertEqual(seen["json"]["model"], "org-model")
        self.assertEqual(chunks[0], ("hi", None))
        self.assertEqual(chunks[-1][1], {"prompt_tokens": 3, "completion_tokens": 2})

    def test_anthropic_stream_headers_and_usage(self):
        seen = {}

        def handler(request):
            seen["url"] = str(request.url)
            seen["key"] = request.headers.get("x-api-key")
            seen["version"] = request.headers.get("anthropic-version")
            return httpx.Response(200, text=(
                'event: message_start\ndata: {"type":"message_start","message":{"usage":{"input_tokens":7}}}\n\n'
                'event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"type":"text_delta","text":"hello"}}\n\n'
                'event: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":4}}\n\n'
                'event: message_stop\ndata: {"type":"message_stop"}\n\n'
            ), headers={"content-type": "text/event-stream"})

        chunks = list(self.call_with_response(handler, lambda: api_client.stream_chat(
            "anthropic", "https://api.example.com", "secret", [{"role": "user", "content": "x"}], "org-model"
        )))
        self.assertEqual(seen["url"], "https://api.example.com/v1/messages")
        self.assertEqual(seen["key"], "secret")
        self.assertEqual(seen["version"], "2023-06-01")
        self.assertEqual(chunks[0], ("hello", None))
        self.assertEqual(chunks[-1][1], {"prompt_tokens": 7, "completion_tokens": 4})

    def test_connection_test_uses_openai_protocol(self):
        seen = {}

        def handler(request):
            seen["url"] = str(request.url)
            seen["payload"] = json.loads(request.content)
            return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

        result = self.call_with_response(handler, lambda: api_client.test_connection(
            "openai", "https://api.example.com/v1", "secret", "org-model"
        ))
        self.assertIn("OpenAI", result)
        self.assertEqual(seen["url"], "https://api.example.com/v1/chat/completions")
        self.assertEqual(seen["payload"]["model"], "org-model")

    def test_legacy_config_migrates_deepseek_model(self):
        old_config_file, old_config_dir = config.CONFIG_FILE, config.CONFIG_DIR
        try:
            config.CONFIG_DIR = Path(__file__).parent / "tmp-config"
            config.CONFIG_FILE = config.CONFIG_DIR / "config.json"
            config.CONFIG_DIR.mkdir(exist_ok=True)
            config.CONFIG_FILE.write_text('{"model":"deepseek-reasoner","height":300}', encoding="utf-8")
            loaded = config.load()
            self.assertEqual(loaded["provider"], "deepseek")
            self.assertEqual(loaded["provider_models"]["deepseek"], "deepseek-reasoner")
        finally:
            config.CONFIG_FILE = old_config_file
            config.CONFIG_DIR = old_config_dir
            try:
                (Path(__file__).parent / "tmp-config" / "config.json").unlink()
                (Path(__file__).parent / "tmp-config").rmdir()
            except OSError:
                pass

    def test_keystore_keeps_legacy_deepseek_account(self):
        with patch.object(keystore.keyring, "get_password", return_value="old-key") as getter:
            self.assertEqual(keystore.get_key("deepseek"), "old-key")
            getter.assert_called_once_with("HoshiriPet", "deepseek")
        with patch.object(keystore.keyring, "set_password") as setter:
            self.assertTrue(keystore.set_key("openai-key", "openai"))
            setter.assert_called_once_with("HoshiriPet", "openai", "openai-key")


if __name__ == "__main__":
    unittest.main()
