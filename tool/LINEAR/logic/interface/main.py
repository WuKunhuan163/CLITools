"""Cross-tool interface for LINEAR."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.LINEAR.main import LINEARTool
except ImportError:
    LINEARTool = None


def get_linear_tool():
    """Return an instance of the LINEAR tool, or None if unavailable."""
    if LINEARTool is None:
        return None
    return LINEARTool()
