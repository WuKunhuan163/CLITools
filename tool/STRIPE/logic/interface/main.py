"""Cross-tool interface for STRIPE."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.STRIPE.main import STRIPETool
except ImportError:
    STRIPETool = None


def get_stripe_tool():
    """Return an instance of the STRIPE tool, or None if unavailable."""
    if STRIPETool is None:
        return None
    return STRIPETool()
