from __future__ import annotations

import sys
import unittest
from datetime import datetime, time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import api_client
import chatter
import config
import environment
import httpx


class Upgrade2Tests(unittest.TestCase):
    def test_config_defaults_and_persona_migration(self):
        original_dir, original_file = config.CONFIG_DIR, config.CONFIG_FILE
        try:
            config.CONFIG_DIR = Path(__file__).parent / "tmp-upgrade-config"
            config.CONFIG_FILE = config.CONFIG_DIR / "config.json"
            config.CONFIG_DIR.mkdir(exist_ok=True)
            config.CONFIG_FILE.write_text('{"height":300}', encoding="utf-8")
            cfg = config.load()
            self.assertNotIn("chatter_interval", cfg)
            self.assertFalse(cfg["quiet_hours_enabled"])
            self.assertIn("星璃", cfg["persona_profile"])
            self.assertFalse(cfg["use_weather"])
        finally:
            config.CONFIG_DIR, config.CONFIG_FILE = original_dir, original_file
            try:
                config.CONFIG_FILE.unlink()
                config.CONFIG_DIR.rmdir()
            except OSError:
                pass

    def test_quiet_hours_across_midnight_and_equal_all_day(self):
        is_quiet = chatter.Chatter._in_quiet_hours
        self.assertTrue(is_quiet(time(23, 30), "23:00", "08:00"))
        self.assertTrue(is_quiet(time(7, 59), "23:00", "08:00"))
        self.assertFalse(is_quiet(time(8, 0), "23:00", "08:00"))
        self.assertTrue(is_quiet(time(12, 0), "12:00", "12:00"))
        self.assertFalse(is_quiet(time(12, 0), "bad", "12:00"))

    def test_chatter_rate_caps_and_quiet_suppression(self):
        c = chatter.Chatter()
        now = datetime(2026, 5, 1, 10, 0)
        self.assertIsNone(c.tick(now, None, 0, False, quiet_enabled=True, quiet_start="09:00", quiet_end="11:00"))
        c.current_gap = c.MIN_GAP
        first = c.tick(now, None, 0, False)
        self.assertIsNotNone(first)
        self.assertIsNone(c.tick(now.replace(minute=5), None, 0, False))
        c.on_user_chat()
        self.assertGreaterEqual(c.current_gap, c.MIN_GAP)

    def test_persona_and_context_are_composed_separately(self):
        prompt = api_client.build_system_prompt("活潑的小夥伴", ["用户喜欢星空"], "设备本地时间：10:00")
        self.assertIn("活潑的小夥伴", prompt)
        self.assertIn("用户喜欢星空", prompt)
        self.assertIn("临时环境上下文", prompt)
        self.assertIn("安全", prompt)
        self.assertNotIn("用户喜欢星空", api_client.build_system_prompt())

    def test_time_context_uses_local_datetime_and_timezone(self):
        from datetime import timezone, timedelta
        current = datetime(2026, 5, 1, 8, 9, tzinfo=timezone(timedelta(hours=8), "CST"))
        text = environment.local_time_context(current)
        self.assertIn("2026-05-01 08:09", text)
        self.assertIn("CST", text)

    def test_weather_failure_degrades_and_cache_avoids_second_request(self):
        environment._weather_cache.clear()
        def handler(request):
            if "geocoding-api" in request.url.host:
                return httpx.Response(200, json={"results": [{"name": "上海", "admin1": "上海市", "country": "中国", "latitude": 31.2, "longitude": 121.5}]})
            return httpx.Response(200, json={"current": {"temperature_2m": 25, "apparent_temperature": 26, "weather_code": 0}})
        real_client = httpx.Client
        calls = []
        def mocked_client(*args, **kwargs):
            transport = httpx.MockTransport(lambda req: (calls.append(str(req.url)), handler(req))[1])
            return real_client(transport=transport, timeout=kwargs.get("timeout"), follow_redirects=False)
        with patch.object(environment.httpx, "Client", side_effect=mocked_client):
            a = environment.weather_context("上海", now=1000)
            b = environment.weather_context("上海", now=1100)
        self.assertIn("25°C", a)
        self.assertEqual(a, b)
        self.assertEqual(len(calls), 2)
        environment._weather_cache.clear()
        with patch.object(environment.httpx, "Client", side_effect=httpx.ConnectError("offline")):
            self.assertEqual(environment.weather_context("未知城市", now=2000), "")

    def test_context_respects_independent_opt_in_switches(self):
        with patch.object(environment, "weather_context", return_value="雨天") as weather:
            self.assertIn("设备本地时间", environment.build_context(use_local_time=True, use_weather=False, city="上海"))
            weather.assert_not_called()
            self.assertEqual(environment.build_context(use_local_time=False, use_weather=True, city="上海"), "雨天")
            weather.assert_called_once_with("上海")


if __name__ == "__main__":
    unittest.main()
