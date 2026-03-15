"""LLM tool configuration management.

Stores API keys and provider settings in ``data/llm_config.json``.

Config format (per-provider):
    {
        "active_backend": "zhipu-glm-4.7",
        "providers": {
            "zhipu": {"api_key": "..."},
            "nvidia": {"api_key": "..."}
        }
    }

Legacy flat keys (e.g. "zhipu_api_key") are automatically migrated
on first read.
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional

_TOOL_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = _TOOL_DIR / "data"
_CONFIG_PATH = _DATA_DIR / "llm_config.json"

_LEGACY_KEY_MAP = {
    "zhipu_api_key": ("zhipu", "api_key"),
    "nvidia_api_key": ("nvidia", "api_key"),
}


def _ensure_data_dir():
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, Any]:
    """Load the LLM configuration, migrating legacy format if needed."""
    if _CONFIG_PATH.exists():
        try:
            cfg = json.loads(_CONFIG_PATH.read_text())
        except Exception:
            cfg = {}
    else:
        cfg = {}

    if _needs_migration(cfg):
        cfg = _migrate(cfg)
        save_config(cfg)

    return cfg


def _needs_migration(cfg: Dict[str, Any]) -> bool:
    return any(key in cfg for key in _LEGACY_KEY_MAP)


def _migrate(cfg: Dict[str, Any]) -> Dict[str, Any]:
    providers = cfg.get("providers", {})
    for old_key, (provider, field) in _LEGACY_KEY_MAP.items():
        if old_key in cfg:
            providers.setdefault(provider, {})[field] = cfg.pop(old_key)
    cfg["providers"] = providers
    return cfg


def save_config(cfg: Dict[str, Any]):
    """Save the LLM configuration."""
    _ensure_data_dir()
    _CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))


def get_config_value(key: str, default=None):
    """Get a config value. Supports both flat and provider-scoped keys.

    For legacy compatibility:
        get_config_value("zhipu_api_key") → providers.zhipu.api_key
    """
    cfg = load_config()

    if key in _LEGACY_KEY_MAP:
        provider, field = _LEGACY_KEY_MAP[key]
        return cfg.get("providers", {}).get(provider, {}).get(field, default)

    return cfg.get(key, default)


def set_config_value(key: str, value):
    """Set a config value. Supports both flat and provider-scoped keys."""
    cfg = load_config()

    if key in _LEGACY_KEY_MAP:
        provider, field = _LEGACY_KEY_MAP[key]
        cfg.setdefault("providers", {}).setdefault(provider, {})[field] = value
    else:
        cfg[key] = value

    save_config(cfg)


def get_provider_config(provider: str) -> Dict[str, Any]:
    """Get the full config dict for a specific provider."""
    return load_config().get("providers", {}).get(provider, {})


def set_provider_config(provider: str, key: str, value: Any):
    """Set a config value for a specific provider."""
    cfg = load_config()
    cfg.setdefault("providers", {}).setdefault(provider, {})[key] = value
    save_config(cfg)
