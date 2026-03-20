"""Cross-tool interface for HEYGEN."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.HEYGEN.main import HEYGENTool
except ImportError:
    HEYGENTool = None


def get_heygen_tool():
    """Return an instance of the HEYGEN tool, or None if unavailable."""
    if HEYGENTool is None:
        return None
    return HEYGENTool()
