from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import chatter


class AdaptiveChatterTests(unittest.TestCase):
    def test_user_engagement_shortens_gap_gradually(self):
        c = chatter.Chatter()
        self.assertEqual(c.current_gap, 3600)
        c.on_user_chat()
        self.assertEqual(c.current_gap, 3300)
        c.on_user_response(datetime(2026, 1, 1, 12, 0))
        self.assertEqual(c.current_gap, 3300)
        c.on_user_response(datetime(2026, 1, 1, 12, 10))
        self.assertEqual(c.current_gap, 3000)

    def test_unanswered_backs_off_without_changing_requested_frequency(self):
        c = chatter.Chatter()
        now = datetime(2026, 5, 1, 12, 0)
        c.last_spoke = now.timestamp()
        c.on_unanswered()
        self.assertEqual(c._unanswered_backoff, 300)
        self.assertIsNone(c.tick(now + timedelta(seconds=60), None, 0, False, frequency_per_minute=1))
        self.assertIsNotNone(c.tick(now + timedelta(seconds=300), None, 0, False, frequency_per_minute=1))
        self.assertEqual(c.MAX_GAP, 10800)

    def test_configured_rate_controls_interval_without_legacy_hour_day_caps(self):
        c = chatter.Chatter()
        now = datetime(2026, 5, 1, 12, 0)
        c.last_spoke = now.timestamp()
        self.assertIsNone(c.tick(now + timedelta(seconds=59), None, 0, False, frequency_per_minute=1))
        self.assertIsNotNone(c.tick(now + timedelta(seconds=60), None, 0, False, frequency_per_minute=1))

        c.last_spoke = now.timestamp()
        c._hour_stamps = [now.timestamp() - 60] * c.MAX_PER_HOUR
        c._day_stamps = [now.timestamp() - 1000] * c.MAX_PER_DAY
        self.assertIsNotNone(c.tick(now + timedelta(minutes=10), None, 0, False, frequency_per_minute=0.1))

    def test_frequency_is_clamped_to_supported_bounds(self):
        c = chatter.Chatter()
        now = datetime(2026, 5, 1, 12, 0)
        c.last_spoke = now.timestamp()
        self.assertIsNone(c.tick(now + timedelta(seconds=5), None, 0, False, frequency_per_minute=1000))
        self.assertIsNotNone(c.tick(now + timedelta(seconds=6), None, 0, False, frequency_per_minute=1000))

        c.last_spoke = now.timestamp()
        self.assertIsNone(c.tick(now + timedelta(seconds=5999), None, 0, False, frequency_per_minute=0.001))
        self.assertIsNotNone(c.tick(now + timedelta(seconds=6000), None, 0, False, frequency_per_minute=0.001))

    def test_disabled_busy_and_quiet_hours_prevent_chatter(self):
        c = chatter.Chatter()
        now = datetime(2026, 5, 1, 12, 0)
        self.assertIsNone(c.tick(now, None, 9999, False, enabled=False, frequency_per_minute=10))
        self.assertIsNone(c.tick(now, None, 9999, True, frequency_per_minute=10))
        self.assertIsNone(c.tick(now.replace(hour=23, minute=30), None, 9999, False,
                                 quiet_enabled=True, quiet_start="23:00", quiet_end="08:00", frequency_per_minute=10))

    def test_no_guilt_trip_lines(self):
        all_lines = [line for lines in chatter.LINES.values() for line in lines]
        self.assertFalse(any("忘了我" in line or "是不是把我忘了" in line for line in all_lines))


if __name__ == "__main__":
    unittest.main()
