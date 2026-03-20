"""Full workflow test — demonstrates the complete CDMCP lifecycle.

Opens a tab, applies all overlays sequentially, verifies each step,
and cleans up. Tests that all operations happen on the SAME tab.
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
from interface.resolve import setup_paths
setup_paths(__file__)

from interface.chrome import (
    is_chrome_cdp_available, find_tab, open_tab,
)
from interface.cdmcp import load_cdmcp_overlay
_ov = load_cdmcp_overlay()
get_session = _ov.get_session
inject_badge = _ov.inject_badge
inject_focus = _ov.inject_focus
inject_lock = _ov.inject_lock
inject_highlight = _ov.inject_highlight
remove_all_overlays = _ov.remove_all_overlays
is_locked = _ov.is_locked
CDMCP_BADGE_ID = _ov.CDMCP_BADGE_ID
CDMCP_FOCUS_ID = _ov.CDMCP_FOCUS_ID
CDMCP_LOCK_ID = _ov.CDMCP_LOCK_ID
CDMCP_HIGHLIGHT_ID = _ov.CDMCP_HIGHLIGHT_ID

EXPECTED_TIMEOUT = 300
EXPECTED_CPU_LIMIT = 40.0

TEST_URL = "https://example.com"
TEST_DOMAIN = "example.com"


def _get_all_overlay_ids(session):
    """Count how many CDMCP overlays exist in the tab."""
    ids = [CDMCP_BADGE_ID, CDMCP_FOCUS_ID, CDMCP_LOCK_ID, CDMCP_HIGHLIGHT_ID]
    result = session.evaluate(f"""
        (function() {{
            var ids = {json.dumps(ids)};
            var found = [];
            ids.forEach(function(id) {{
                if (document.getElementById(id)) found.push(id);
            }});
            return JSON.stringify(found);
        }})()
    """)
    try:
        return json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return []


@unittest.skipUnless(
    is_chrome_cdp_available(),
    "Chrome CDP not available on port 9222"
)
class TestFullWorkflow(unittest.TestCase):
    """End-to-end CDMCP overlay workflow on a single tab."""

    def test_complete_lifecycle(self):
        """Navigate -> Badge -> Focus -> Lock -> Highlight -> Verify -> Cleanup."""
        tab = find_tab(TEST_DOMAIN)
        if not tab:
            open_tab(TEST_URL)
            time.sleep(2)
            tab = find_tab(TEST_DOMAIN)

        self.assertIsNotNone(tab, "Test tab should be available")
        session = get_session(tab)
        self.assertIsNotNone(session, "Should connect to test tab")

        try:
            # Step 1: Inject badge
            self.assertTrue(inject_badge(session, text="CDMCP-TEST"))
            found = _get_all_overlay_ids(session)
            self.assertIn(CDMCP_BADGE_ID, found)

            # Step 2: Inject focus border
            self.assertTrue(inject_focus(session))
            found = _get_all_overlay_ids(session)
            self.assertIn(CDMCP_FOCUS_ID, found)

            # Step 3: Inject lock overlay
            self.assertTrue(inject_lock(session))
            self.assertTrue(is_locked(session))
            found = _get_all_overlay_ids(session)
            self.assertIn(CDMCP_LOCK_ID, found)

            # Step 4: Highlight an element (through the lock)
            result = inject_highlight(session, "h1", label="Example Domain")
            self.assertTrue(result.get("ok"))
            found = _get_all_overlay_ids(session)
            self.assertEqual(len(found), 4, "All 4 overlays should be present")

            # Step 5: Verify element info returned by highlight
            self.assertIn("element", result)
            self.assertEqual(result["element"]["tag"], "h1")
            self.assertIn("rect", result)

            # Step 6: Cleanup
            removed = remove_all_overlays(session)
            self.assertGreater(len(removed.get("removed", [])), 0)

            # Verify clean state
            found = _get_all_overlay_ids(session)
            self.assertEqual(len(found), 0, "No overlays should remain after cleanup")

        finally:
            session.close()


@unittest.skipUnless(
    is_chrome_cdp_available(),
    "Chrome CDP not available on port 9222"
)
class TestTabPinning(unittest.TestCase):
    """Test that multiple operations target the same tab, not random ones."""

    def test_operations_stay_on_same_tab(self):
        """All overlay operations should target the same tab via find_tab."""
        tab1 = find_tab(TEST_DOMAIN)
        if not tab1:
            open_tab(TEST_URL)
            time.sleep(2)
            tab1 = find_tab(TEST_DOMAIN)

        self.assertIsNotNone(tab1)
        tab_id = tab1.get("id")

        # Perform multiple find_tab calls — should return the same tab
        for _ in range(5):
            tab_n = find_tab(TEST_DOMAIN)
            self.assertIsNotNone(tab_n)
            self.assertEqual(tab_n.get("id"), tab_id,
                             "find_tab should consistently return the same tab")


if __name__ == "__main__":
    unittest.main()
