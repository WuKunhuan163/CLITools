"""Cross-tool interface for WPS."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.WPS.main import WPSTool
except ImportError:
    WPSTool = None


def get_wps_tool():
    """Return an instance of the WPS tool, or None if unavailable."""
    if WPSTool is None:
        return None
    return WPSTool()
