"""Visual overlay test for CDMCP — verifies badge, focus, lock, and highlight.

Requires Chrome running with --remote-debugging-port=9222.
Opens a test page and verifies each overlay layer is injected and removable.
"""
import unittest
import sys
import time
import json
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.chrome.session import is_chrome_cdp_available, find_tab, open_tab, close_tab, CDP_PORT
from logic.cdmcp_loader import load_cdmcp_overlay
_ov = load_cdmcp_overlay()
get_session = _ov.get_session
get_session_for_url = _ov.get_session_for_url
inject_badge = _ov.inject_badge
remove_badge = _ov.remove_badge
inject_focus = _ov.inject_focus
remove_focus = _ov.remove_focus
inject_lock = _ov.inject_lock
remove_lock = _ov.remove_lock
is_locked = _ov.is_locked
inject_highlight = _ov.inject_highlight
remove_highlight = _ov.remove_highlight
inject_all_overlays = _ov.inject_all_overlays
remove_all_overlays = _ov.remove_all_overlays
CDMCP_BADGE_ID = _ov.CDMCP_BADGE_ID
CDMCP_FOCUS_ID = _ov.CDMCP_FOCUS_ID
CDMCP_LOCK_ID = _ov.CDMCP_LOCK_ID
CDMCP_HIGHLIGHT_ID = _ov.CDMCP_HIGHLIGHT_ID

TEST_URL = "https://example.com"
TEST_DOMAIN = "example.com"

EXPECTED_TIMEOUT = 300
EXPECTED_CPU_LIMIT = 40.0


def _ensure_test_tab():
    """Open a test tab and ensure it loads example.com correctly."""
    from logic.chrome.session import CDPSession as _CDP
    tab = find_tab(TEST_DOMAIN)
    if tab:
        ws = tab.get("webSocketDebuggerUrl")
        if ws:
            s = _CDP(ws)
            url = s.evaluate("window.location.href") or ""
            if "example.com" not in str(url):
                s.evaluate(f"window.location.href = '{TEST_URL}'")
                time.sleep(2)
            s.close()
            tab = find_tab(TEST_DOMAIN)
            return tab
    open_tab(TEST_URL)
    time.sleep(2)
    return find_tab(TEST_DOMAIN)


def _element_exists(session, element_id):
    """Check if a DOM element with the given id exists."""
    return session.evaluate(
        f"!!document.getElementById('{element_id}')"
    ) is True


@unittest.skipUnless(
    is_chrome_cdp_available(),
    "Chrome CDP not available on port 9222"
)
class TestOverlayVisual(unittest.TestCase):
    """Test all CDMCP overlay visual effects on a live Chrome tab."""

    @classmethod
    def setUpClass(cls):
        cls.tab = _ensure_test_tab()
        if not cls.tab:
            raise unittest.SkipTest("Could not open test tab")
        cls.session = get_session(cls.tab)
        if not cls.session:
            raise unittest.SkipTest("Could not connect to test tab")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "session") and cls.session:
            remove_all_overlays(cls.session)
            cls.session.close()

    # --- Badge ---

    def test_01_inject_badge(self):
        """Badge is injected and visible in the DOM."""
        result = inject_badge(self.session)
        self.assertTrue(result, "Badge injection should return True")
        self.assertTrue(
            _element_exists(self.session, CDMCP_BADGE_ID),
            "Badge element should exist in DOM"
        )

    def test_02_badge_content(self):
        """Badge displays the correct text."""
        inject_badge(self.session, text="TEST-CDMCP")
        text = self.session.evaluate(
            f"document.getElementById('{CDMCP_BADGE_ID}')?.textContent"
        )
        self.assertEqual(text, "TEST-CDMCP")

    def test_03_remove_badge(self):
        inject_badge(self.session)
        result = remove_badge(self.session)
        self.assertTrue(result)
        self.assertFalse(_element_exists(self.session, CDMCP_BADGE_ID))

    # --- Focus ---

    def test_04_inject_focus(self):
        result = inject_focus(self.session)
        self.assertTrue(result, "Focus injection should return True")
        self.assertTrue(
            _element_exists(self.session, CDMCP_FOCUS_ID),
            "Focus element should exist in DOM"
        )

    def test_05_focus_border_style(self):
        inject_focus(self.session, color="#ff0000")
        border = self.session.evaluate(
            f"document.getElementById('{CDMCP_FOCUS_ID}')?.style.border"
        )
        self.assertTrue(
            "ff0000" in (border or "") or "rgb(255, 0, 0)" in (border or ""),
            f"Expected red border, got: {border}"
        )

    def test_06_remove_focus(self):
        inject_focus(self.session)
        result = remove_focus(self.session)
        self.assertTrue(result)
        self.assertFalse(_element_exists(self.session, CDMCP_FOCUS_ID))

    # --- Lock ---

    def test_07_inject_lock(self):
        result = inject_lock(self.session)
        self.assertTrue(result, "Lock injection should return True")
        self.assertTrue(
            _element_exists(self.session, CDMCP_LOCK_ID),
            "Lock overlay should exist in DOM"
        )

    def test_08_lock_state(self):
        inject_lock(self.session)
        self.assertTrue(is_locked(self.session), "Tab should report as locked")

    def test_09_lock_has_label(self):
        inject_lock(self.session)
        text = self.session.evaluate(
            f"document.getElementById('{CDMCP_LOCK_ID}')?.querySelector('div')?.textContent"
        )
        self.assertIn("unlock", (text or "").lower())

    def test_10_remove_lock(self):
        inject_lock(self.session)
        result = remove_lock(self.session)
        self.assertTrue(result)
        self.assertFalse(_element_exists(self.session, CDMCP_LOCK_ID))
        self.assertFalse(is_locked(self.session))

    # --- Highlight ---

    def test_11_inject_highlight(self):
        result = inject_highlight(self.session, "h1", label="Main Heading")
        self.assertTrue(result.get("ok"), f"Highlight should succeed: {result}")
        self.assertTrue(
            _element_exists(self.session, CDMCP_HIGHLIGHT_ID),
            "Highlight element should exist in DOM"
        )

    def test_12_highlight_returns_element_info(self):
        result = inject_highlight(self.session, "h1", label="Test")
        self.assertTrue(result.get("ok"))
        self.assertIn("element", result)
        self.assertEqual(result["element"]["tag"], "h1")
        self.assertIn("rect", result)
        self.assertGreater(result["rect"]["width"], 0)

    def test_13_highlight_nonexistent_element(self):
        result = inject_highlight(self.session, "#nonexistent_element_xyz")
        self.assertFalse(result.get("ok"))
        self.assertIn("error", result)

    def test_14_remove_highlight(self):
        inject_highlight(self.session, "h1")
        result = remove_highlight(self.session)
        self.assertTrue(result)
        self.assertFalse(_element_exists(self.session, CDMCP_HIGHLIGHT_ID))

    # --- Composite ---

    def test_15_inject_all_overlays(self):
        results = inject_all_overlays(self.session, locked=True, focus=True)
        self.assertTrue(results.get("badge"))
        self.assertTrue(results.get("focus"))
        self.assertTrue(results.get("lock"))

        self.assertTrue(_element_exists(self.session, CDMCP_BADGE_ID))
        self.assertTrue(_element_exists(self.session, CDMCP_FOCUS_ID))
        self.assertTrue(_element_exists(self.session, CDMCP_LOCK_ID))

    def test_16_remove_all_overlays(self):
        inject_all_overlays(self.session, locked=True, focus=True)
        result = remove_all_overlays(self.session)
        removed = result.get("removed", [])
        self.assertGreater(len(removed), 0)

        self.assertFalse(_element_exists(self.session, CDMCP_BADGE_ID))
        self.assertFalse(_element_exists(self.session, CDMCP_FOCUS_ID))
        self.assertFalse(_element_exists(self.session, CDMCP_LOCK_ID))

    # --- Tab consistency: all overlays on same tab ---

    def test_17_overlays_on_same_tab(self):
        """Verify all overlays are injected into the same tab (not scattered)."""
        inject_all_overlays(self.session, locked=True, focus=True)
        inject_highlight(self.session, "h1", label="Heading")

        count = self.session.evaluate(f"""
            (function() {{
                var ids = {json.dumps([CDMCP_BADGE_ID, CDMCP_FOCUS_ID, CDMCP_LOCK_ID, CDMCP_HIGHLIGHT_ID])};
                var count = 0;
                ids.forEach(function(id) {{
                    if (document.getElementById(id)) count++;
                }});
                return count;
            }})()
        """)
        self.assertEqual(count, 4, "All 4 overlay elements should be in the same tab")
        remove_all_overlays(self.session)


@unittest.skipUnless(
    is_chrome_cdp_available(),
    "Chrome CDP not available on port 9222"
)
class TestOverlayIdempotency(unittest.TestCase):
    """Overlays should be idempotent — re-injection replaces, not duplicates."""

    @classmethod
    def setUpClass(cls):
        cls.tab = _ensure_test_tab()
        if not cls.tab:
            raise unittest.SkipTest("Could not open test tab")
        cls.session = get_session(cls.tab)
        if not cls.session:
            raise unittest.SkipTest("Could not connect to test tab")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "session") and cls.session:
            remove_all_overlays(cls.session)
            cls.session.close()

    def test_double_badge_no_duplicate(self):
        inject_badge(self.session)
        inject_badge(self.session)
        count = self.session.evaluate(
            f"document.querySelectorAll('#{CDMCP_BADGE_ID}').length"
        )
        self.assertEqual(count, 1)

    def test_double_focus_no_duplicate(self):
        inject_focus(self.session)
        inject_focus(self.session)
        count = self.session.evaluate(
            f"document.querySelectorAll('#{CDMCP_FOCUS_ID}').length"
        )
        self.assertEqual(count, 1)

    def test_double_lock_no_duplicate(self):
        inject_lock(self.session)
        inject_lock(self.session)
        count = self.session.evaluate(
            f"document.querySelectorAll('#{CDMCP_LOCK_ID}').length"
        )
        self.assertEqual(count, 1)
        remove_lock(self.session)


if __name__ == "__main__":
    unittest.main()
