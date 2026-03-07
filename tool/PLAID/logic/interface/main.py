"""Cross-tool interface for PLAID."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.PLAID.main import PLAIDTool
except ImportError:
    PLAIDTool = None


def get_plaid_tool():
    """Return an instance of the PLAID tool, or None if unavailable."""
    if PLAIDTool is None:
        return None
    return PLAIDTool()
