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
