"""Cross-tool interface for SENTRY."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.SENTRY.main import SENTRYTool
except ImportError:
    SENTRYTool = None


def get_sentry_tool():
    """Return an instance of the SENTRY tool, or None if unavailable."""
    if SENTRYTool is None:
        return None
    return SENTRYTool()
