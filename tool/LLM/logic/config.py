"""LLM tool configuration management.

Provider-specific data (API keys, key states, credentials) is stored
per-provider in ``providers/<vendor>/data/keys.json``.

General settings (active_backend, turn limits, etc.) are stored in
``tool/LLM/data/settings.json``.
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional

_TOOL_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = _TOOL_DIR / "data"
_SETTINGS_PATH = _DATA_DIR / "settings.json"
_PROVIDERS_DIR = Path(__file__).resolve().parent / "providers"

_LEGACY_KEY_MAP = {
    "zhipu_api_key": ("zhipu", "api_key"),
    "nvidia_api_key": ("nvidia", "api_key"),
    "google_api_key": ("google", "api_key"),
    "baidu_api_key": ("baidu", "api_key"),
    "tencent_api_key": ("tencent", "api_key"),
    "siliconflow_api_key": ("siliconflow", "api_key"),
}


def _ensure_data_dir():
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _provider_keys_path(provider: str) -> Path:
    return _PROVIDERS_DIR / provider / "data" / "keys.json"


def _load_provider_keys(provider: str) -> Dict[str, Any]:
    p = _provider_keys_path(provider)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def _save_provider_keys(provider: str, data: Dict[str, Any]):
    p = _provider_keys_path(provider)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_config() -> Dict[str, Any]:
    """Load general settings + all provider configs (unified view).

    Returns a dict like the old config.json format for backward compatibility:
    {"active_backend": "...", "providers": {"zhipu": {...}, ...}, ...}
    """
    settings = _load_settings()

    # Merge provider data from per-provider keys.json
    providers = {}
    if _PROVIDERS_DIR.is_dir():
        for d in _PROVIDERS_DIR.iterdir():
            if d.is_dir() and not d.name.startswith("_") and d.name != "__pycache__":
                pdata = _load_provider_keys(d.name)
                if pdata:
                    providers[d.name] = pdata

    cfg = dict(settings)
    cfg["providers"] = providers
    return cfg


def _load_settings() -> Dict[str, Any]:
    if _SETTINGS_PATH.exists():
        try:
            return json.loads(_SETTINGS_PATH.read_text())
        except Exception:
            return {}
    return {}


def _save_settings(settings: Dict[str, Any]):
    _ensure_data_dir()
    filtered = {k: v for k, v in settings.items() if k != "providers"}
    _SETTINGS_PATH.write_text(json.dumps(filtered, indent=2, ensure_ascii=False))


def save_config(cfg: Dict[str, Any]):
    """Save config. Provider data goes to per-provider keys.json,
    general settings to settings.json."""
    providers = cfg.get("providers", {})
    for vendor, pcfg in providers.items():
        _save_provider_keys(vendor, pcfg)

    settings = {k: v for k, v in cfg.items() if k != "providers"}
    _save_settings(settings)


def get_config_value(key: str, default=None):
    """Get a config value. Supports both flat and provider-scoped keys."""
    if key in _LEGACY_KEY_MAP:
        provider, field = _LEGACY_KEY_MAP[key]
        pcfg = _load_provider_keys(provider)
        if field == "api_key":
            keys = pcfg.get("api_keys", [])
            if keys:
                return keys[0].get("key", default)
        return pcfg.get(field, default)

    return _load_settings().get(key, default)


def set_config_value(key: str, value):
    """Set a config value. Supports both flat and provider-scoped keys."""
    if key in _LEGACY_KEY_MAP:
        provider, field = _LEGACY_KEY_MAP[key]
        pcfg = _load_provider_keys(provider)
        if field == "api_key":
            keys = pcfg.get("api_keys", [])
            if keys:
                keys[0]["key"] = value
            else:
                pcfg["api_keys"] = [{"id": "0", "key": value, "label": "default"}]
        else:
            pcfg[field] = value
        _save_provider_keys(provider, pcfg)
    else:
        settings = _load_settings()
        settings[key] = value
        _save_settings(settings)


def get_provider_config(provider: str) -> Dict[str, Any]:
    """Get the full config dict for a specific provider."""
    return _load_provider_keys(provider)


def set_provider_config(provider: str, key: str, value: Any):
    """Set a config value for a specific provider."""
    pcfg = _load_provider_keys(provider)
    pcfg[key] = value
    _save_provider_keys(provider, pcfg)


def get_credentials(provider: str) -> Dict[str, str]:
    """Get multi-field credentials for a provider."""
    pcfg = _load_provider_keys(provider)
    creds = pcfg.get("credentials", {})
    if creds:
        return creds
    single = pcfg.get("api_key", "")
    if single:
        return {"api_key": single}
    keys = pcfg.get("api_keys", [])
    if keys:
        return {"api_key": keys[0].get("key", "")}
    return {}


def set_credentials(provider: str, credentials: Dict[str, str]):
    """Set multi-field credentials for a provider."""
    pcfg = _load_provider_keys(provider)
    pcfg["credentials"] = credentials
    _save_provider_keys(provider, pcfg)


def get_api_keys(provider: str) -> list:
    """Get all API keys for a provider. Returns list of {id, key, label} dicts."""
    pcfg = _load_provider_keys(provider)
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
    pcfg = _load_provider_keys(provider)
    keys = pcfg.get("api_keys", [])

    if not keys and pcfg.get("api_key"):
        keys.append({"id": "0", "key": pcfg.pop("api_key"), "label": "default"})

    kid = str(uuid.uuid4())[:8]
    keys.append({"id": kid, "key": key, "label": label or f"key-{kid[:4]}"})
    pcfg["api_keys"] = keys
    _save_provider_keys(provider, pcfg)
    return kid


def remove_api_key(provider: str, key_id: str) -> bool:
    """Remove an API key by ID. Returns True if found and removed."""
    pcfg = _load_provider_keys(provider)
    keys = pcfg.get("api_keys", [])
    before = len(keys)
    keys = [k for k in keys if k.get("id") != key_id]
    if len(keys) == before:
        return False
    pcfg["api_keys"] = keys
    _save_provider_keys(provider, pcfg)
    return True


def reorder_api_keys(provider: str, key_ids: list):
    """Reorder API keys by providing the list of key IDs in desired order."""
    pcfg = _load_provider_keys(provider)
    keys = {k["id"]: k for k in pcfg.get("api_keys", [])}
    pcfg["api_keys"] = [keys[kid] for kid in key_ids if kid in keys]
    _save_provider_keys(provider, pcfg)


class APIKeyRotator:
    """Rotate through multiple API keys for a provider."""

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
        if self._keys:
            self._index = (self._index + 1) % len(self._keys)

    def reset(self):
        self._index = 0

    def reload(self):
        self._keys = get_api_keys(self._provider)
        if self._index >= len(self._keys):
            self._index = 0
