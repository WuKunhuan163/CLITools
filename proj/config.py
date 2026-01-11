import json
from pathlib import Path

# Project root is parent of proj/
PROJECT_ROOT = Path(__file__).parent.parent
COLORS_JSON = PROJECT_ROOT / "proj" / "colors.json"

def get_color(color_name, default="\033[0m"):
    """Retrieve an ANSI color code from colors.json."""
    try:
        if COLORS_JSON.exists():
            with open(COLORS_JSON, 'r') as f:
                colors = json.load(f)
                return colors.get(color_name, default)
    except Exception:
        pass
    return default
