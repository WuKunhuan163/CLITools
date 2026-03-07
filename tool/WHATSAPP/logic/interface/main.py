"""Cross-tool interface for WHATSAPP."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.WHATSAPP.main import WHATSAPPTool
except ImportError:
    WHATSAPPTool = None


def get_whatsapp_tool():
    """Return an instance of the WHATSAPP tool, or None if unavailable."""
    if WHATSAPPTool is None:
        return None
    return WHATSAPPTool()
