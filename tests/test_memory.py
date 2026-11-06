from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import memory
import config


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = Path(self.temp_dir.name) / "memory-test.db"
        self.cfg_dir, self.cfg_file = config.CONFIG_DIR, config.CONFIG_FILE
        config.CONFIG_DIR = Path(self.temp_dir.name)
        config.CONFIG_FILE = Path(self.temp_dir.name) / "config.json"
        self.db_patch = patch.object(memory, "DB_FILE", self.db_file)
        self.db_patch.start()
        with memory._conn():
            pass

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()
        config.CONFIG_DIR, config.CONFIG_FILE = self.cfg_dir, self.cfg_file

    def test_only_confirmed_memories_are_retrieved(self):
        memory.add("喜欢星空和夜晚")
        self.assertEqual(memory.retrieve("我喜欢星空"), ["喜欢星空和夜晚"])

    def test_candidate_is_conservative_and_sensitive_is_blocked(self):
        self.assertEqual(memory.candidate_from_user_message("我喜欢星空"), "我喜欢星空")
        self.assertIsNone(memory.candidate_from_user_message("密码是 abc123"))
        self.assertIsNone(memory.candidate_from_user_message("今天我喝了咖啡"))

    def test_ignore_is_remembered_and_sensitive_add_fails(self):
        memory.ignore_candidate("喜欢星空")
        self.assertTrue(memory.is_ignored("喜欢星空"))
        with self.assertRaises(ValueError):
            memory.add("我的 API Key 是 abc")

    def test_recall_respects_opt_out_and_length_limit(self):
        memory.add("我喜欢星空和天文摄影")
        with patch.object(config, "load", return_value={"memory_enabled": False}):
            self.assertEqual(memory.retrieve("星空天文摄影", max_chars=4), [])
        with patch.object(memory, "MAX_RECALL_CHARS", 4):
            self.assertEqual(memory.retrieve("星空天文摄影", max_chars=4), [])

    def test_edit_delete_and_clear(self):
        memory_id = memory.add("喜欢星空")
        memory.update(memory_id, "喜歡觀星")
        self.assertEqual(memory.list_memories()[0]["content"], "喜歡觀星")
        memory.delete(memory_id)
        self.assertEqual(memory.list_memories(), [])
        memory.add("喜欢阅读科幻小说")
        memory.clear_all()
        self.assertEqual(memory.list_memories(), [])


if __name__ == "__main__":
    unittest.main()
