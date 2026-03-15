"""Unit tests for USERINPUT queue claiming (bare USERINPUT with queued items)."""
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


class TestQueueClaim(unittest.TestCase):
    def setUp(self):
        self._backup = None
        if QUEUE_FILE.exists():
            self._backup = QUEUE_FILE.read_text()

    def tearDown(self):
        if self._backup is not None:
            QUEUE_FILE.write_text(self._backup)
        else:
            _set_queue([])

    def test_claim_from_queue(self):
        _set_queue(["Claim me", "Next task"])
        res = _run()
        self.assertEqual(res.returncode, 0)
        self.assertIn("Claim me", res.stdout)
        self.assertIn("from queue", res.stdout.lower())
        remaining = _get_queue()
        self.assertEqual(remaining, ["Next task"])

    def test_claim_shows_remaining(self):
        _set_queue(["Task1", "Task2", "Task3"])
        res = _run()
        self.assertEqual(res.returncode, 0)
        self.assertIn("Task1", res.stdout)
        self.assertIn("2 remaining", res.stdout.lower())

    def test_enquiry_bypasses_queue(self):
        _set_queue(["Queued task"])
        res = _run("--enquiry", "--timeout", "2")
        # --enquiry should bypass the queue, so "Queued task" should NOT be in output
        # Instead it should attempt to open the GUI (which will timeout)
        self.assertNotIn("Queued task", res.stdout)
        remaining = _get_queue()
        self.assertEqual(remaining, ["Queued task"])


if __name__ == "__main__":
    unittest.main()
