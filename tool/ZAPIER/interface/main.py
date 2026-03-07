"""Cross-tool interface for ZAPIER."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.ZAPIER.main import ZAPIERTool
except ImportError:
    ZAPIERTool = None


def get_zapier_tool():
    """Return an instance of the ZAPIER tool, or None if unavailable."""
    if ZAPIERTool is None:
        return None
    return ZAPIERTool()
