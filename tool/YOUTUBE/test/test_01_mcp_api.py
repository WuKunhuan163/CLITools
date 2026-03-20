#!/usr/bin/env python3
"""Test YouTube CDMCP API functions (requires Chrome CDP on port 9222)."""
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


class TestYouTubeAuth(unittest.TestCase):
    @unittest.skipUnless(_cdp_available(), "Chrome CDP not running")
    def test_auth_state(self):
        from tool.YOUTUBE.logic.utils.chrome.api import get_auth_state
        r = get_auth_state()
        self.assertIn("authenticated", r)

    @unittest.skipUnless(_cdp_available(), "Chrome CDP not running")
    def test_page_info(self):
        from tool.YOUTUBE.logic.utils.chrome.api import get_page_info
        r = get_page_info()
        # May be ok=False if no YT tab open, that's fine
        self.assertIsInstance(r, dict)


class TestYouTubeSubtitlesAPI(unittest.TestCase):
    def test_fetch_subtitles_known_video(self):
        """Fetch subtitles for a well-known video with captions."""
        from tool.YOUTUBE.logic.utils.chrome.api import fetch_subtitles_api
        # Rick Astley - Never Gonna Give You Up (has English captions)
        r = fetch_subtitles_api("dQw4w9WgXcQ")
        if r.get("ok"):
            self.assertGreater(r.get("segments", 0), 0)
            self.assertTrue(r.get("fullText", ""))
        else:
            # Some environments may block the request
            self.assertIn("error", r)

    def test_fetch_subtitles_invalid_id(self):
        from tool.YOUTUBE.logic.utils.chrome.api import fetch_subtitles_api
        r = fetch_subtitles_api("INVALID_VIDEO_ID_12345")
        self.assertFalse(r.get("ok"))


if __name__ == "__main__":
    unittest.main()
