"""Cross-tool interface for SQUARE."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.SQUARE.main import SQUARETool
except ImportError:
    SQUARETool = None


def get_square_tool():
    """Return an instance of the SQUARE tool, or None if unavailable."""
    if SQUARETool is None:
        return None
    return SQUARETool()
