"""Cross-tool interface for KIMI."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.KIMI.main import KIMITool
except ImportError:
    KIMITool = None


def get_kimi_tool():
    """Return an instance of the KIMI tool, or None if unavailable."""
    if KIMITool is None:
        return None
    return KIMITool()
