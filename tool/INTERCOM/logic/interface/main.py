"""Cross-tool interface for INTERCOM."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.INTERCOM.main import INTERCOMTool
except ImportError:
    INTERCOMTool = None


def get_intercom_tool():
    """Return an instance of the INTERCOM tool, or None if unavailable."""
    if INTERCOMTool is None:
        return None
    return INTERCOMTool()
