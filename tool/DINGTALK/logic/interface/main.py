"""Cross-tool interface for DINGTALK."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.DINGTALK.main import DINGTALKTool
except ImportError:
    DINGTALKTool = None


def get_dingtalk_tool():
    """Return an instance of the DINGTALK tool, or None if unavailable."""
    if DINGTALKTool is None:
        return None
    return DINGTALKTool()
