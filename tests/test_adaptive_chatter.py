from __future__ import annotations

import sys
import unittest
from datetime import datetime
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
        self.assertEqual(c.current_gap, 3300)  # first response only resets unanswered counter
        c.on_user_response(datetime(2026, 1, 1, 12, 10))
        self.assertEqual(c.current_gap, 3000)

    def test_unanswered_backs_off_with_hard_cap(self):
        c = chatter.Chatter()
        c.on_unanswered()
        self.assertEqual(c.current_gap, 3900)
        for _ in range(100):
            c.on_unanswered()
        self.assertEqual(c.current_gap, c.MAX_GAP)

    def test_hard_cooldown_and_quiet_hours(self):
        c = chatter.Chatter()
        c.current_gap = c.MIN_GAP
        c.last_spoke = datetime(2026, 5, 1, 12, 0).timestamp()
        self.assertIsNone(c.tick(datetime(2026, 5, 1, 12, 14), None, 9999, False))
        self.assertIsNone(c.tick(datetime(2026, 5, 1, 23, 30), None, 9999, False,
                                 quiet_enabled=True, quiet_start="23:00", quiet_end="08:00"))

    def test_hour_and_day_caps(self):
        c = chatter.Chatter()
        now = datetime(2026, 5, 1, 12, 0)
        c.current_gap = c.MIN_GAP
        c._hour_stamps = [now.timestamp() - 60] * c.MAX_PER_HOUR
        self.assertIsNone(c.tick(now, None, 9999, False))
        c._hour_stamps.clear()
        c._day_stamps = [now.timestamp() - 1000] * c.MAX_PER_DAY
        self.assertIsNone(c.tick(now, None, 9999, False))

    def test_no_guilt_trip_lines(self):
        all_lines = [line for lines in chatter.LINES.values() for line in lines]
        self.assertFalse(any("忘了我" in line or "是不是把我忘了" in line for line in all_lines))


if __name__ == "__main__":
    unittest.main()
