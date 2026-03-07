"""Cross-tool interface for ATLASSIAN."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.ATLASSIAN.main import ATLASSIANTool
except ImportError:
    ATLASSIANTool = None


def get_atlassian_tool():
    """Return an instance of the ATLASSIAN tool, or None if unavailable."""
    if ATLASSIANTool is None:
        return None
    return ATLASSIANTool()
