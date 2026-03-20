"""Test XMIND state and session APIs (requires active Chrome CDP)."""
import sys
from pathlib import Path

_PROJ = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_PROJ))
from interface.resolve import setup_paths
setup_paths(str(_PROJ / "tool" / "XMIND" / "main.py"))

import pytest

try:
    from interface.chrome import is_chrome_cdp_available
    CDP_AVAILABLE = is_chrome_cdp_available()
except Exception:
    CDP_AVAILABLE = False


@pytest.mark.skipif(not CDP_AVAILABLE, reason="Chrome CDP not available")
class TestXMindState:
    def test_session_status(self):
        from tool.XMIND.logic.chrome.api import get_session_status
        r = get_session_status()
        assert r.get("ok") is True
        assert "state" in r

    def test_mcp_state(self):
        from tool.XMIND.logic.chrome.api import get_mcp_state
        r = get_mcp_state()
        assert r.get("ok") is True
        assert "nodes" in r or "node_count" in r
        assert "url" in r

    def test_get_map_nodes(self):
        from tool.XMIND.logic.chrome.api import get_map_nodes
        r = get_map_nodes()
        assert r.get("ok") is True
        assert isinstance(r.get("nodes"), list)

    def test_get_auth_state(self):
        from tool.XMIND.logic.chrome.api import get_auth_state
        r = get_auth_state()
        assert r.get("ok") is True
        assert "authenticated" in r


if __name__ == "__main__":
    if not CDP_AVAILABLE:
        print("SKIP: Chrome CDP not available")
        sys.exit(0)
    t = TestXMindState()
    t.test_session_status()
    print("PASS: session_status")
    t.test_mcp_state()
    print("PASS: mcp_state")
    t.test_get_map_nodes()
    print("PASS: get_map_nodes")
    t.test_get_auth_state()
    print("PASS: get_auth_state")
