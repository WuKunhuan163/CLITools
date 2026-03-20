"""Unit tests for USERINPUT --queue CLI commands."""
import unittest
import subprocess
import sys
import os
import json
from pathlib import Path

EXPECTED_TIMEOUT = 30
SEQUENTIAL = True

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BIN = PROJECT_ROOT / "bin" / "USERINPUT" / "USERINPUT"
if not BIN.exists():
    BIN = PROJECT_ROOT / "bin" / "USERINPUT"
QUEUE_FILE = PROJECT_ROOT / "tool" / "USERINPUT" / "logic" / "queue.json"


def _run(*args, **kwargs):
    env = os.environ.copy()
    env["TOOL_LANGUAGE"] = "en"
    return subprocess.run(
        [sys.executable, str(BIN)] + list(args),
        capture_output=True, text=True, env=env, **kwargs
    )


def _set_queue(items):
    QUEUE_FILE.write_text(json.dumps({"prompts": items}, ensure_ascii=False))


def _get_queue():
    if not QUEUE_FILE.exists():
        return []
    return json.loads(QUEUE_FILE.read_text()).get("prompts", [])


class TestQueueCLI(unittest.TestCase):
    def setUp(self):
        self._backup = None
        if QUEUE_FILE.exists():
            self._backup = QUEUE_FILE.read_text()
        _set_queue([])

    def tearDown(self):
        if self._backup is not None:
            QUEUE_FILE.write_text(self._backup)
        else:
            _set_queue([])

    def test_queue_list_empty(self):
        res = _run("--queue", "--list")
        self.assertEqual(res.returncode, 0)
        self.assertIn("empty", res.stdout.lower())

    def test_queue_add(self):
        res = _run("--queue", "--add", "Test prompt alpha")
        self.assertEqual(res.returncode, 0)
        items = _get_queue()
        self.assertEqual(items, ["Test prompt alpha"])

    def test_queue_add_multiple_then_list(self):
        _run("--queue", "--add", "First")
        _run("--queue", "--add", "Second")
        res = _run("--queue", "--list")
        self.assertEqual(res.returncode, 0)
        self.assertIn("0:", res.stdout)
        self.assertIn("1:", res.stdout)
        self.assertIn("First", res.stdout)
        self.assertIn("Second", res.stdout)

    def test_queue_delete(self):
        _set_queue(["A", "B", "C"])
        res = _run("--queue", "--delete", "1")
        self.assertEqual(res.returncode, 0)
        self.assertEqual(_get_queue(), ["A", "C"])

    def test_queue_delete_invalid(self):
        _set_queue(["A"])
        res = _run("--queue", "--delete", "99")
        self.assertNotEqual(res.returncode, 0)

    def test_queue_move_up(self):
        _set_queue(["A", "B", "C"])
        res = _run("--queue", "--move-up", "2")
        self.assertEqual(res.returncode, 0)
        self.assertEqual(_get_queue(), ["A", "C", "B"])

    def test_queue_move_down(self):
        _set_queue(["A", "B", "C"])
        res = _run("--queue", "--move-down", "0")
        self.assertEqual(res.returncode, 0)
        self.assertEqual(_get_queue(), ["B", "A", "C"])

    def test_queue_move_to_top(self):
        _set_queue(["A", "B", "C"])
        res = _run("--queue", "--move-to-top", "2")
        self.assertEqual(res.returncode, 0)
        self.assertEqual(_get_queue(), ["C", "A", "B"])

    def test_queue_move_to_bottom(self):
        _set_queue(["A", "B", "C"])
        res = _run("--queue", "--move-to-bottom", "0")
        self.assertEqual(res.returncode, 0)
        self.assertEqual(_get_queue(), ["B", "C", "A"])


if __name__ == "__main__":
    unittest.main()
