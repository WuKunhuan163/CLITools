"""Cross-tool interface for GITLAB."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.GITLAB.main import GITLABTool
except ImportError:
    GITLABTool = None


def get_gitlab_tool():
    """Return an instance of the GITLAB tool, or None if unavailable."""
    if GITLABTool is None:
        return None
    return GITLABTool()
