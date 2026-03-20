"""LLM tool configuration management.

Stores API keys and provider settings in ``data/llm_config.json``.
"""
import json
from pathlib import Path
from typing import Dict, Any

_TOOL_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = _TOOL_DIR / "data"
_CONFIG_PATH = _DATA_DIR / "llm_config.json"


def _ensure_data_dir():
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, Any]:
    """Load the LLM configuration."""
    if _CONFIG_PATH.exists():
        try:
            return json.loads(_CONFIG_PATH.read_text())
        except Exception:
            pass
    return {}


def save_config(cfg: Dict[str, Any]):
    """Save the LLM configuration."""
    _ensure_data_dir()
    _CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def get_config_value(key: str, default=None):
    """Get a single config value."""
    return load_config().get(key, default)


def set_config_value(key: str, value):
    """Set a single config value."""
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
