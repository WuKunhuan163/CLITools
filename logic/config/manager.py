import json
import sys
from pathlib import Path
from typing import Any, Dict

def print_width_check(width, is_auto=False, actual_detected=True, project_root=None, translation_func=None):
    """Unified display for terminal width check."""
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    if is_auto:
        if not actual_detected:
            status = f"{_('config_width_unknown', 'unknown')} ({_('config_using_fallback', 'using fallback')}: {width}. Use TOOL config --terminal-width-fallback xx to change the fallback value.)"
        else:
            status = str(width)
        print(_("config_updated_dynamic", "Global configuration updated: {key} will be calculated dynamically.", key="terminal_width") + " Current detected width: " + status)
    else:
        print(_("config_updated", "Global configuration updated: {key} = {value}", key="terminal_width", value=width))
    
    print("\n" + _("config_check_row", "Please check whether the below line of '=' ({width}) exactly expands one terminal row:", width=width))
    from logic.utils import print_terminal_width_separator
    print_terminal_width_separator(width)
    print("")
    """Manages tool-specific configuration."""
    def __init__(self, tool_name: str, tool_script_dir: Path):
        self.tool_name = tool_name
        self.config_dir = tool_script_dir / "data" / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.config_dir / "config.json"
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                # Handle corrupted config file
                print(f"Warning: Config file for {self.tool_name} is corrupted. Resetting to default.", file=sys.stderr)
                return {}
        return {}

    def _save_config(self):
        with open(self.config_path, 'w') as f:
            json.dump(self._config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value, supporting dot notation."""
        parts = key.split('.')
        current = self._config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def set(self, key: str, value: Any):
        """Set a configuration value, supporting dot notation."""
        parts = key.split('.')
        current = self._config
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                current[part] = value
            else:
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]
        self._save_config()

    def delete(self, key: str):
        """Delete a configuration value, supporting dot notation."""
        parts = key.split('.')
        current = self._config
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                if part in current:
                    del current[part]
                    self._save_config()
                return
            else:
                if part not in current or not isinstance(current[part], dict):
                    return # Key not found
                current = current[part]
