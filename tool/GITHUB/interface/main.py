"""Cross-tool interface for GITHUB."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.GITHUB.main import GITHUBTool
except ImportError:
    GITHUBTool = None


def get_github_tool():
    """Return an instance of the GITHUB tool, or None if unavailable."""
    if GITHUBTool is None:
        return None
    return GITHUBTool()
