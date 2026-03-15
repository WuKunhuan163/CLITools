"""Unit tests for USERINPUT --system-prompt --add/--delete/--list/--move-* management."""
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
CONFIG_FILE = PROJECT_ROOT / "tool" / "USERINPUT" / "logic" / "config.json"


def _run(*args, **kwargs):
    env = os.environ.copy()
    env["TOOL_LANGUAGE"] = "en"
    return subprocess.run(
        [sys.executable, str(BIN)] + list(args),
        capture_output=True, text=True, env=env, **kwargs
    )


def _get_prompts():
    if not CONFIG_FILE.exists():
        return []
    with open(CONFIG_FILE) as f:
        return json.load(f).get("system_prompt", [])


def _set_prompts(prompts):
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    else:
        config = {}
    config["system_prompt"] = prompts
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


class TestSystemPrompts(unittest.TestCase):
    def setUp(self):
        self._backup = None
        if CONFIG_FILE.exists():
            self._backup = CONFIG_FILE.read_text()

    def tearDown(self):
        if self._backup is not None:
            CONFIG_FILE.write_text(self._backup)

    def test_system_prompt_list(self):
        res = _run("--system-prompt", "--list")
        self.assertEqual(res.returncode, 0)

    def test_system_prompt_add(self):
        original = _get_prompts()
        test_prompt = "Unit test prompt via --add"
        res = _run("--system-prompt", "--add", test_prompt)
        self.assertEqual(res.returncode, 0)
        new_prompts = _get_prompts()
        self.assertIn(test_prompt, new_prompts)
        _set_prompts(original)

    def test_system_prompt_delete(self):
        original = _get_prompts()
        _set_prompts(["Keep", "Delete me", "Also keep"])
        res = _run("--system-prompt", "--delete", "1")
        self.assertEqual(res.returncode, 0)
        self.assertEqual(_get_prompts(), ["Keep", "Also keep"])
        _set_prompts(original)

    def test_system_prompt_move_up(self):
        original = _get_prompts()
        _set_prompts(["A", "B", "C"])
        res = _run("--system-prompt", "--move-up", "2")
        self.assertEqual(res.returncode, 0)
        self.assertEqual(_get_prompts(), ["A", "C", "B"])
        _set_prompts(original)

    def test_system_prompt_move_down(self):
        original = _get_prompts()
        _set_prompts(["A", "B", "C"])
        res = _run("--system-prompt", "--move-down", "0")
        self.assertEqual(res.returncode, 0)
        self.assertEqual(_get_prompts(), ["B", "A", "C"])
        _set_prompts(original)


if __name__ == "__main__":
    unittest.main()
