"""Cross-tool interface for MIDJOURNEY."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.MIDJOURNEY.main import MIDJOURNEYTool
except ImportError:
    MIDJOURNEYTool = None


def get_midjourney_tool():
    """Return an instance of the MIDJOURNEY tool, or None if unavailable."""
    if MIDJOURNEYTool is None:
        return None
    return MIDJOURNEYTool()
