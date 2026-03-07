"""Cross-tool interface for SUNO."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.SUNO.main import SUNOTool
except ImportError:
    SUNOTool = None


def get_suno_tool():
    """Return an instance of the SUNO tool, or None if unavailable."""
    if SUNOTool is None:
        return None
    return SUNOTool()
