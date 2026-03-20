import json
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def get_gui_config():
    """Retrieve GUI style configuration from global config."""
    config_path = PROJECT_ROOT / "data" / "config.json"
    default_style = {
        "font_family": "Arial",
        "label_font_size": 10,
        "button_font_size": 10,
        "primary_button_font_size": 10,
        "status_font_size": 12,
        "primary_button_weight": "bold",
        "status_color_blue": "#007AFF", # macOS like blue
        "status_color_green": "#28A745",
        "status_color_red": "#DC3545",
        "status_pulse_color": "#007AFF" # Restore to classic blue
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
                # Merge with defaults
                style = data.get("gui_style", {})
                for k, v in default_style.items():
                    if k not in style:
                        style[k] = v
                return style
        except: pass
    return default_style

def get_label_style():
    cfg = get_gui_config()
    return (cfg["font_family"], cfg["label_font_size"])

def get_secondary_label_style():
    cfg = get_gui_config()
    return (cfg["font_family"], cfg["label_font_size"] - 1, "italic")

def get_button_style(primary=False):
    cfg = get_gui_config()
    weight = cfg["primary_button_weight"] if primary else "normal"
    size = cfg["primary_button_font_size"] if primary else cfg["button_font_size"]
    return (cfg["font_family"], size, weight)

def get_status_style():
    cfg = get_gui_config()
    return (cfg["font_family"], cfg["status_font_size"])

def get_gui_colors():
    cfg = get_gui_config()
    return {
        "blue": cfg["status_color_blue"],
        "green": cfg["status_color_green"],
        "red": cfg["status_color_red"],
        "pulse": cfg["status_pulse_color"]
    }

