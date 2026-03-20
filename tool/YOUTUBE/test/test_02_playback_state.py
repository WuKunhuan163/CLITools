#!/usr/bin/env python3
"""Test YouTube playback controls and state reporting (requires Chrome CDP)."""
import sys
import unittest
from pathlib import Path

_r = Path(__file__).resolve().parent.parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)

EXPECTED_TIMEOUT = 300
EXPECTED_CPU_LIMIT = 40.0


def _cdp_available():
    from interface.chrome import is_chrome_cdp_available
    return is_chrome_cdp_available()


@unittest.skipUnless(_cdp_available(), "Chrome CDP not running")
class TestMCPState(unittest.TestCase):
    def test_get_mcp_state(self):
        from tool.YOUTUBE.logic.utils.chrome.api import get_mcp_state
        r = get_mcp_state()
        self.assertIsInstance(r, dict)
        if r.get("ok"):
            self.assertIn("url", r)
            self.assertIn("section", r)
            self.assertIn("machine_state", r)

    def test_session_status(self):
        from tool.YOUTUBE.logic.utils.chrome.api import get_session_status
        r = get_session_status()
        self.assertIn("state", r)
        self.assertIn("cdp_available", r)


@unittest.skipUnless(_cdp_available(), "Chrome CDP not running")
class TestPlayback(unittest.TestCase):
    def test_play(self):
        from tool.YOUTUBE.logic.utils.chrome.api import play
        r = play()
        self.assertIsInstance(r, dict)

    def test_pause(self):
        from tool.YOUTUBE.logic.utils.chrome.api import pause
        r = pause()
        self.assertIsInstance(r, dict)

    def test_volume_get(self):
        from tool.YOUTUBE.logic.utils.chrome.api import volume
        r = volume()
        self.assertIsInstance(r, dict)
        if r.get("ok"):
            self.assertIn("volume", r)
            self.assertIn("muted", r)

    def test_speed_get(self):
        from tool.YOUTUBE.logic.utils.chrome.api import speed
        r = speed()
        self.assertIsInstance(r, dict)
        if r.get("ok"):
            self.assertIn("speed", r)

    def test_captions_check(self):
        from tool.YOUTUBE.logic.utils.chrome.api import captions
        r = captions()
        self.assertIsInstance(r, dict)
        if r.get("ok"):
            self.assertIn("captions", r)


@unittest.skipUnless(_cdp_available(), "Chrome CDP not running")
class TestNavigation(unittest.TestCase):
    def test_navigate_known_target(self):
        from tool.YOUTUBE.logic.utils.chrome.api import navigate
        r = navigate("home")
        self.assertIsInstance(r, dict)

    def test_navigate_invalid(self):
        from tool.YOUTUBE.logic.utils.chrome.api import navigate
        r = navigate("not_a_valid_section")
        self.assertFalse(r.get("ok"))

    def test_get_recommendations(self):
        from tool.YOUTUBE.logic.utils.chrome.api import get_recommendations
        r = get_recommendations(limit=3)
        self.assertIsInstance(r, dict)


if __name__ == "__main__":
    unittest.main()
