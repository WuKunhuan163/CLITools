import json
from pathlib import Path

# Project root is three levels up: logic/config/main.py -> logic/config -> logic -> root
PROJECT_ROOT = Path(__file__).parent.parent.parent
COLORS_JSON = Path(__file__).parent / "colors.json"
SETTINGS_JSON = Path(__file__).parent / "settings.json"

def get_setting(key, default=None):
    """Retrieve a setting from settings.json."""
    try:
        if SETTINGS_JSON.exists():
            with open(SETTINGS_JSON, 'r') as f:
                return json.load(f).get(key, default)
    except Exception:
        pass
    return default

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
