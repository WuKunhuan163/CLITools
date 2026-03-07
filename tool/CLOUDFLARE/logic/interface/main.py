"""Cross-tool interface for CLOUDFLARE."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.CLOUDFLARE.main import CLOUDFLARETool
except ImportError:
    CLOUDFLARETool = None


def get_cloudflare_tool():
    """Return an instance of the CLOUDFLARE tool, or None if unavailable."""
    if CLOUDFLARETool is None:
        return None
    return CLOUDFLARETool()
