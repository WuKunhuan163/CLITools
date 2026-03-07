"""Cross-tool interface for PAYPAL."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.PAYPAL.main import PAYPALTool
except ImportError:
    PAYPALTool = None


def get_paypal_tool():
    """Return an instance of the PAYPAL tool, or None if unavailable."""
    if PAYPALTool is None:
        return None
    return PAYPALTool()
