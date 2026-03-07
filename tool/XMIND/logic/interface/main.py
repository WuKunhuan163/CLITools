"""Cross-tool interface for XMIND."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.XMIND.main import XMINDTool
except ImportError:
    XMINDTool = None


def get_xmind_tool():
    """Return an instance of the XMIND tool, or None if unavailable."""
    if XMINDTool is None:
        return None
    return XMINDTool()
