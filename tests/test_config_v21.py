from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config


class ConfigV21Tests(unittest.TestCase):
    def test_legacy_short_persona_migrates_and_frequency_defaults_conservatively(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg_dir = Path(directory)
            config_file = cfg_dir / "config.json"
            legacy = {"chatter_interval": "frequent", "persona": {
                "personality": "旧性格设定", "style": "旧说话风格", "address": "伙伴", "boundaries": "旧边界"}}
            config_file.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
            with patch.object(config, "CONFIG_DIR", cfg_dir), patch.object(config, "CONFIG_FILE", config_file):
                loaded = config.load()
                self.assertNotIn("chatter_interval", loaded)
                self.assertEqual(loaded["chatter_frequency_per_minute"], 0.02)
                for old in ("旧性格设定", "旧说话风格", "伙伴", "旧边界"):
                    self.assertIn(old, loaded["persona_profile"])
                config.save(loaded)
                saved = json.loads(config_file.read_text(encoding="utf-8"))
                self.assertNotIn("chatter_interval", saved)
                self.assertEqual(saved["chatter_frequency_per_minute"], 0.02)
                self.assertIn("旧边界", saved["persona_profile"])

    def test_old_builtin_persona_is_upgraded_once(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg_dir = Path(directory)
            config_file = cfg_dir / "config.json"
            old_default = "exact previous shipped default persona"
            config_file.write_text(json.dumps({"persona_profile": old_default}), encoding="utf-8")
            with patch.object(config, "CONFIG_DIR", cfg_dir), patch.object(config, "CONFIG_FILE", config_file), \
                 patch.object(config, "LEGACY_DEFAULT_PERSONA_SHA256", hashlib.sha256(old_default.encode("utf-8")).hexdigest()):
                upgraded = config.load()
                self.assertEqual(upgraded["persona_profile"], config.DEFAULT_PERSONA)
                self.assertEqual(upgraded["persona_schema_version"], config.PERSONA_SCHEMA_VERSION)
                saved = json.loads(config_file.read_text(encoding="utf-8"))
                self.assertEqual(saved["persona_profile"], config.DEFAULT_PERSONA)
                self.assertEqual(saved["persona_schema_version"], config.PERSONA_SCHEMA_VERSION)
                reopened = config.load()
                self.assertEqual(reopened["persona_profile"], config.DEFAULT_PERSONA)

    def test_custom_persona_is_never_overwritten_by_default_upgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg_dir = Path(directory)
            config_file = cfg_dir / "config.json"
            custom = "我自己写的星璃档案，保持原样。"
            config_file.write_text(json.dumps({"persona_profile": custom}), encoding="utf-8")
            with patch.object(config, "CONFIG_DIR", cfg_dir), patch.object(config, "CONFIG_FILE", config_file):
                loaded = config.load()
                self.assertEqual(loaded["persona_profile"], custom)
                saved = json.loads(config_file.read_text(encoding="utf-8"))
                self.assertEqual(saved["persona_profile"], custom)

    def test_frequency_config_is_clamped_and_invalid_values_fall_back(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg_dir = Path(directory)
            config_file = cfg_dir / "config.json"
            with patch.object(config, "CONFIG_DIR", cfg_dir), patch.object(config, "CONFIG_FILE", config_file):
                for value, expected in [(0, 0.01), (100, 10.0), ("invalid", 0.02), (float("nan"), 0.02)]:
                    config_file.write_text(json.dumps({"chatter_frequency_per_minute": value}), encoding="utf-8")
                    self.assertEqual(config.load()["chatter_frequency_per_minute"], expected)

    def test_provider_defaults_are_official_but_explicit_custom_urls_are_kept(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg_dir = Path(directory)
            config_file = cfg_dir / "config.json"
            with patch.object(config, "CONFIG_DIR", cfg_dir), patch.object(config, "CONFIG_FILE", config_file):
                defaults = config.load()
                self.assertEqual(defaults["provider_urls"]["openai"], "https://api.openai.com/v1")
                self.assertEqual(defaults["provider_urls"]["anthropic"], "https://api.anthropic.com")
                self.assertEqual(defaults["provider_models"]["openai"], "gpt-4o-mini")
                self.assertEqual(defaults["provider_models"]["anthropic"], "claude-3-5-sonnet-latest")
                config_file.write_text(json.dumps({"provider_urls": {"openai": "https://custom.example/v1", "anthropic": "https://custom.example/anthropic"}}), encoding="utf-8")
                custom = config.load()
                self.assertEqual(custom["provider_urls"]["openai"], "https://custom.example/v1")
                self.assertEqual(custom["provider_urls"]["anthropic"], "https://custom.example/anthropic")

    def test_explicit_custom_urls_round_trip_without_reverting_to_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg_dir = Path(directory)
            config_file = cfg_dir / "config.json"
            custom_urls = {
                "openai": "https://company-gateway.example/v1",
                "anthropic": "https://bobo-work.txlrai.cn",
            }
            config_file.write_text(json.dumps({"provider_urls": custom_urls}), encoding="utf-8")
            with patch.object(config, "CONFIG_DIR", cfg_dir), patch.object(config, "CONFIG_FILE", config_file):
                loaded = config.load()
                self.assertEqual(loaded["provider_urls"]["openai"], custom_urls["openai"])
                self.assertEqual(loaded["provider_urls"]["anthropic"], custom_urls["anthropic"])
                config.save(loaded)
                reopened = config.load()
                self.assertEqual(reopened["provider_urls"], loaded["provider_urls"])

    def test_explicit_legacy_relay_url_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg_dir = Path(directory)
            config_file = cfg_dir / "config.json"
            legacy_custom = "https://bobo-work.txlrai.cn/v1"
            config_file.write_text(json.dumps({"provider_urls": {"openai": legacy_custom}}), encoding="utf-8")
            with patch.object(config, "CONFIG_DIR", cfg_dir), patch.object(config, "CONFIG_FILE", config_file):
                loaded = config.load()
                self.assertEqual(loaded["provider_urls"]["openai"], legacy_custom)


if __name__ == "__main__":
    unittest.main()
