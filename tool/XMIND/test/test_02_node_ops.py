"""Test XMIND node operations (requires active Chrome CDP + open map)."""
import sys
import time
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
class TestNodeOperations:
    def _node_texts(self):
        from tool.XMIND.logic.utils.chrome.api import get_map_nodes
        r = get_map_nodes()
        return [n["text"] for n in r.get("nodes", [])]

    def test_add_and_delete_node(self):
        from tool.XMIND.logic.utils.chrome.api import add_node, delete_node
        r = add_node(parent_text="Central Topic", text="UnitTestNode")
        assert r.get("ok"), f"add_node failed: {r}"
        time.sleep(1)
        nodes = self._node_texts()
        assert "UnitTestNode" in nodes, f"Node not found in {nodes}"

        r = delete_node("UnitTestNode")
        assert r.get("ok"), f"delete_node failed: {r}"
        time.sleep(1)
        nodes = self._node_texts()
        assert "UnitTestNode" not in nodes, f"Node still present in {nodes}"

    def test_edit_node(self):
        from tool.XMIND.logic.utils.chrome.api import add_node, edit_node, delete_node
        add_node(parent_text="Central Topic", text="EditMe")
        time.sleep(1)

        r = edit_node("EditMe", "Edited")
        assert r.get("ok"), f"edit_node failed: {r}"
        time.sleep(1)
        nodes = self._node_texts()
        assert "Edited" in nodes

        delete_node("Edited")
        time.sleep(1)

    def test_undo_redo(self):
        from tool.XMIND.logic.utils.chrome.api import add_node, undo, redo, delete_node
        add_node(parent_text="Central Topic", text="UndoTest")
        time.sleep(1)

        undo()
        time.sleep(1)
        nodes = self._node_texts()
        assert "UndoTest" not in nodes, "Undo didn't remove node"

        redo()
        time.sleep(1)
        nodes = self._node_texts()
        assert "UndoTest" in nodes, "Redo didn't restore node"

        delete_node("UndoTest")
        time.sleep(0.5)


if __name__ == "__main__":
    if not CDP_AVAILABLE:
        print("SKIP: Chrome CDP not available")
        sys.exit(0)
    t = TestNodeOperations()
    t.test_add_and_delete_node()
    print("PASS: add_and_delete_node")
    t.test_edit_node()
    print("PASS: edit_node")
    t.test_undo_redo()
    print("PASS: undo_redo")
