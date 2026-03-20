"""Session configuration persistence."""
from __future__ import annotations
from pathlib import Path

_dir = Path(__file__).parent.parent
_root = _dir.parent.parent.parent


class ConfigMixin:
    """Session configuration persistence."""

    def _save_session_config(self, key, value) -> dict:
        """Save a single session config key from the frontend settings panel.

        If the key exists in SESSION_SETTINGS_SCHEMA, the value is validated
        against the defined min/max range and clamped accordingly.
        """
        if not key:
            return {"ok": False, "error": "Missing key"}
        try:
            from tool.LLM.logic.config import load_config, save_config
            cfg = load_config()
            try:
                value = float(value)
                if value == int(value):
                    value = int(value)
            except (ValueError, TypeError):
                pass
            schema_entry = next(
                (s for s in self.SESSION_SETTINGS_SCHEMA if s["key"] == key), None
            )
            if schema_entry and isinstance(value, (int, float)):
                clamped = max(schema_entry["min"], min(schema_entry["max"], value))
                if "options" in schema_entry:
                    opts = schema_entry["options"]
                    value = min(opts, key=lambda o: abs(o - clamped))
                elif isinstance(schema_entry["default"], float):
                    value = float(clamped)
                else:
                    value = int(clamped)
            cfg[key] = value
            save_config(cfg)
            return {"ok": True, "key": key, "value": value}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    SESSION_SETTINGS_SCHEMA = [
        {"key": "compression_ratio", "default": 0.5, "min": 0.25, "max": 0.75,
         "mode": "percent", "step": 0.05, "tab": "chat",
         "desc": "Compress context when it reaches this % of the model's max context window."},
        {"key": "context_lines", "default": 2, "min": 0, "max": 10,
         "mode": "options", "options": [0, 1, 2, 5, 10], "tab": "chat",
         "desc": "Number of surrounding context lines shown around diffs and file reads."},
        {"key": "history_context_rounds", "default": 8, "min": 1, "max": 64,
         "mode": "pow2", "tab": "chat",
         "desc": "Number of recent rounds whose full data is retained for prompt engineering."},
    ]

    def _get_session_config(self) -> dict:
        """Return session config values and their full schema.

        The schema includes key, default, min, max, mode, and description
        for each setting, so the frontend can render controls dynamically
        without hardcoding these values.
        """
        try:
            from tool.LLM.logic.config import get_config_value
            config = {}
            for s in self.SESSION_SETTINGS_SCHEMA:
                val = get_config_value(s["key"], s["default"])
                try:
                    config[s["key"]] = int(val)
                except (ValueError, TypeError):
                    config[s["key"]] = s["default"]

            extra_defaults = {
                "default_turn_limit": 20,
                "compression_ratio": 0.5,
            }
            for key, default in extra_defaults.items():
                val = get_config_value(key, default)
                try:
                    config[key] = float(val) if isinstance(default, float) else int(val)
                except (ValueError, TypeError):
                    config[key] = default

            return {
                "ok": True,
                "config": config,
                "schema": self.SESSION_SETTINGS_SCHEMA,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}
