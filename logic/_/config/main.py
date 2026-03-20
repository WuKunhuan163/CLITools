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

def get_global_config(key=None, default=None):
    """Retrieve a configuration value from data/config.json."""
    try:
        config_path = PROJECT_ROOT / "data" / "config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                if key:
                    return config.get(key, default)
                return config
    except Exception:
        pass
    return default if key else {}

def set_global_config(key, value):
    """Update a configuration value in data/config.json."""
    try:
        config_path = PROJECT_ROOT / "data" / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        config[key] = value
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False

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
