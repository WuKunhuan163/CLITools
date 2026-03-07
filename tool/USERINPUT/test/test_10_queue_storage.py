"""Unit tests for the queue storage module (logic/queue.py)."""
import unittest
import sys
import json
from pathlib import Path

EXPECTED_TIMEOUT = 30
SEQUENTIAL = True

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "userinput_queue",
    str(PROJECT_ROOT / "tool" / "USERINPUT" / "logic" / "queue.py")
)
_qmod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_qmod)

QUEUE_FILE = _qmod.QUEUE_FILE


class TestQueueStorage(unittest.TestCase):
    def setUp(self):
        self._backup = None
        if QUEUE_FILE.exists():
            self._backup = QUEUE_FILE.read_text()
        _qmod.replace_all([])

    def tearDown(self):
        if self._backup is not None:
            QUEUE_FILE.write_text(self._backup)
        elif QUEUE_FILE.exists():
            _qmod.replace_all([])

    def test_add_and_list(self):
        _qmod.add("Task A")
        _qmod.add("Task B")
        items = _qmod.list_all()
        self.assertEqual(items, ["Task A", "Task B"])

    def test_claim_fifo(self):
        _qmod.add("First")
        _qmod.add("Second")
        claimed = _qmod.claim()
        self.assertEqual(claimed, "First")
        self.assertEqual(_qmod.list_all(), ["Second"])

    def test_claim_empty(self):
        self.assertIsNone(_qmod.claim())

    def test_remove(self):
        _qmod.replace_all(["A", "B", "C"])
        self.assertTrue(_qmod.remove(1))
        self.assertEqual(_qmod.list_all(), ["A", "C"])

    def test_remove_invalid(self):
        _qmod.replace_all(["A"])
        self.assertFalse(_qmod.remove(5))

    def test_move_up(self):
        _qmod.replace_all(["A", "B", "C"])
        self.assertTrue(_qmod.move_up(2))
        self.assertEqual(_qmod.list_all(), ["A", "C", "B"])

    def test_move_down(self):
        _qmod.replace_all(["A", "B", "C"])
        self.assertTrue(_qmod.move_down(0))
        self.assertEqual(_qmod.list_all(), ["B", "A", "C"])

    def test_move_to_top(self):
        _qmod.replace_all(["A", "B", "C"])
        self.assertTrue(_qmod.move_to_top(2))
        self.assertEqual(_qmod.list_all(), ["C", "A", "B"])

    def test_move_to_bottom(self):
        _qmod.replace_all(["A", "B", "C"])
        self.assertTrue(_qmod.move_to_bottom(0))
        self.assertEqual(_qmod.list_all(), ["B", "C", "A"])

    def test_count(self):
        _qmod.replace_all(["X", "Y"])
        self.assertEqual(_qmod.count(), 2)

    def test_replace_all(self):
        _qmod.replace_all(["New1", "New2", "New3"])
        self.assertEqual(_qmod.list_all(), ["New1", "New2", "New3"])


if __name__ == "__main__":
    unittest.main()
