from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config


class ConfigV21Tests(unittest.TestCase):
    def test_legacy_short_persona_is_migrated_without_loss_and_frequency_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg_dir = Path(directory)
            config_file = cfg_dir / "config.json"
            legacy = {"chatter_interval": "frequent", "persona": {
                "personality": "旧性格设定", "style": "旧说话风格", "address": "伙伴", "boundaries": "旧边界"}}
            config_file.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
            with patch.object(config, "CONFIG_DIR", cfg_dir), patch.object(config, "CONFIG_FILE", config_file):
                loaded = config.load()
                self.assertNotIn("chatter_interval", loaded)
                for old in ("旧性格设定", "旧说话风格", "伙伴", "旧边界"):
                    self.assertIn(old, loaded["persona_profile"])
                config.save(loaded)
                saved = json.loads(config_file.read_text(encoding="utf-8"))
                self.assertNotIn("chatter_interval", saved)
                self.assertIn("旧边界", saved["persona_profile"])

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

    def test_retired_bobowork_relay_defaults_migrate_to_official_endpoints(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg_dir = Path(directory)
            config_file = cfg_dir / "config.json"
            old = {"provider_urls": {"openai": "https://bobo-work.txlrai.cn/v1", "anthropic": "https://bobo-work.txlrai.cn"}}
            config_file.write_text(json.dumps(old), encoding="utf-8")
            with patch.object(config, "CONFIG_DIR", cfg_dir), patch.object(config, "CONFIG_FILE", config_file):
                migrated = config.load()
                self.assertEqual(migrated["provider_urls"]["openai"], "https://api.openai.com/v1")
                self.assertEqual(migrated["provider_urls"]["anthropic"], "https://api.anthropic.com")


if __name__ == "__main__":
    unittest.main()
