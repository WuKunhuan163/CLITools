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


def get_api_keys(provider: str) -> list:
    """Get all API keys for a provider. Returns list of {id, key, label} dicts.

    Supports both legacy single-key and new multi-key format.
    Legacy format: {"api_key": "xxx"} → [{"id": "0", "key": "xxx", "label": "default"}]
    Multi format:  {"api_keys": [{"id": "...", "key": "...", "label": "..."}]}
    """
    pcfg = get_provider_config(provider)
    keys = pcfg.get("api_keys", [])
    if keys:
        return keys
    single = pcfg.get("api_key", "")
    if single:
        return [{"id": "0", "key": single, "label": "default"}]
    return []


def add_api_key(provider: str, key: str, label: str = "") -> str:
    """Add a new API key for a provider. Returns the assigned key ID."""
    import uuid
    cfg = load_config()
    pcfg = cfg.setdefault("providers", {}).setdefault(provider, {})
    keys = pcfg.get("api_keys", [])

    if not keys and pcfg.get("api_key"):
        keys.append({"id": "0", "key": pcfg.pop("api_key"), "label": "default"})

    kid = str(uuid.uuid4())[:8]
    keys.append({"id": kid, "key": key, "label": label or f"key-{kid[:4]}"})
    pcfg["api_keys"] = keys
    save_config(cfg)
    return kid


def remove_api_key(provider: str, key_id: str) -> bool:
    """Remove an API key by ID. Returns True if found and removed."""
    cfg = load_config()
    pcfg = cfg.get("providers", {}).get(provider, {})
    keys = pcfg.get("api_keys", [])
    before = len(keys)
    keys = [k for k in keys if k.get("id") != key_id]
    if len(keys) == before:
        return False
    pcfg["api_keys"] = keys
    save_config(cfg)
    return True


def reorder_api_keys(provider: str, key_ids: list):
    """Reorder API keys by providing the list of key IDs in desired order."""
    cfg = load_config()
    pcfg = cfg.get("providers", {}).get(provider, {})
    keys = {k["id"]: k for k in pcfg.get("api_keys", [])}
    pcfg["api_keys"] = [keys[kid] for kid in key_ids if kid in keys]
    save_config(cfg)


class APIKeyRotator:
    """Rotate through multiple API keys for a provider.

    Tries keys in order. On 429 or auth failure, advances to the next key.
    Cycles back to the first key after exhausting all.
    """

    def __init__(self, provider: str):
        self._provider = provider
        self._keys = get_api_keys(provider)
        self._index = 0

    @property
    def current_key(self) -> Optional[str]:
        if not self._keys:
            return None
        return self._keys[self._index % len(self._keys)].get("key")

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def advance(self):
        """Move to the next API key (on rate limit or auth failure)."""
        if self._keys:
            self._index = (self._index + 1) % len(self._keys)

    def reset(self):
        """Reset to the first key."""
        self._index = 0

    def reload(self):
        """Reload keys from config (if keys were added/removed)."""
        self._keys = get_api_keys(self._provider)
        if self._index >= len(self._keys):
            self._index = 0
