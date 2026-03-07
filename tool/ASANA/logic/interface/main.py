"""Cross-tool interface for ASANA."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.ASANA.main import ASANATool
except ImportError:
    ASANATool = None


def get_asana_tool():
    """Return an instance of the ASANA tool, or None if unavailable."""
    if ASANATool is None:
        return None
    return ASANATool()
