"""Hooks engine — discover, load, enable/disable, and fire hook instances.

Directory layout per tool:

    <TOOL>/hooks/
    ├── interface/           # Hook event definitions (abstract base)
    │   └── on_start.py      # class OnStartHook(HookInterface): ...
    ├── instance/            # Concrete implementations
    │   └── auto_save.py     # class AutoSaveHook(OnStartHook): ...
    └── config.json          # {"enabled": ["auto_save"], "disabled": []}

The engine:
  1. Discovers all interfaces (hook events the tool can fire).
  2. Discovers all instances (concrete handlers).
  3. Loads config.json to know which instances are active.
  4. Provides fire(event_name, **kwargs) to invoke all enabled handlers
     registered for that event.
"""

import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional


class HookInterface:
    """Base class for hook event definitions.

    Subclass in <TOOL>/hooks/interface/<event>.py to declare a hook.
    Each subclass defines:
      - event_name: str  (e.g. "on_tool_start")
      - description: str
    """
    event_name: str = ""
    desc: str = ""

    def validate_kwargs(self, kwargs: dict) -> bool:
        """Optional: validate the kwargs passed when the event fires."""
        return True


class HookInstance:
    """Base class for hook implementations.

    Subclass in <TOOL>/hooks/instance/<name>.py to create a handler.
    Each subclass defines:
      - name: str              (unique identifier, matches filename)
      - description: str
      - event_name: str        (which event this handles)
      - execute(**kwargs)      (the actual callback logic)
    """
    name: str = ""
    desc: str = ""
    event_name: str = ""
    enabled_by_default: bool = False

    def execute(self, **kwargs) -> Any:
        """Run the hook logic. Override in subclass."""
        raise NotImplementedError


class HooksEngine:
    """Per-tool hooks manager."""

    def __init__(self, tool_dir: Path, tool_name: str = "",
                 project_root: Path = None):
        self.tool_dir = tool_dir
        self.tool_name = tool_name
        self.project_root = project_root or tool_dir.parent.parent
        self.hooks_dir = tool_dir / "hooks"
        self._interfaces: Dict[str, HookInterface] = {}
        self._instances: Dict[str, HookInstance] = {}
        self._config: Dict[str, Any] = {"enabled": [], "disabled": []}
        self._config_path = self.hooks_dir / "config.json"

        # Also check base hooks from the framework
        self._base_hooks_dir = self.project_root / "logic" / "tool" / "hooks" / "base"

        self._load_config()
        self._discover_interfaces()
        self._discover_instances()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _load_module(self, path: Path, module_name: str):
        """Load a Python module from file path."""
        if not path.exists():
            return None
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if spec is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            return mod
        except Exception:
            return None

    def _discover_interfaces(self):
        """Find all HookInterface subclasses from interface/ directories."""
        dirs = []
        # Base interfaces (from logic/tool/hooks/base/interface/)
        base_iface_dir = self._base_hooks_dir / "interface"
        if base_iface_dir.exists():
            dirs.append(base_iface_dir)
        # Tool-specific interfaces
        tool_iface_dir = self.hooks_dir / "interface"
        if tool_iface_dir.exists():
            dirs.append(tool_iface_dir)

        for d in dirs:
            for py_file in sorted(d.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue
                mod = self._load_module(py_file, f"hook_iface_{py_file.stem}")
                if mod is None:
                    continue
                for attr_name in dir(mod):
                    obj = getattr(mod, attr_name)
                    if (isinstance(obj, type)
                            and issubclass(obj, HookInterface)
                            and obj is not HookInterface
                            and getattr(obj, "event_name", "")):
                        self._interfaces[obj.event_name] = obj()

    def _discover_instances(self):
        """Find all HookInstance subclasses from instance/ directories."""
        dirs = []
        # Base instances (from logic/tool/hooks/base/instance/)
        base_inst_dir = self._base_hooks_dir / "instance"
        if base_inst_dir.exists():
            dirs.append(base_inst_dir)
        # Tool-specific instances
        tool_inst_dir = self.hooks_dir / "instance"
        if tool_inst_dir.exists():
            dirs.append(tool_inst_dir)

        for d in dirs:
            for py_file in sorted(d.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue
                mod = self._load_module(py_file, f"hook_inst_{py_file.stem}")
                if mod is None:
                    continue
                for attr_name in dir(mod):
                    obj = getattr(mod, attr_name)
                    if (isinstance(obj, type)
                            and issubclass(obj, HookInstance)
                            and obj is not HookInstance
                            and getattr(obj, "name", "")):
                        self._instances[obj.name] = obj()

    # ------------------------------------------------------------------
    # Config (enabled / disabled)
    # ------------------------------------------------------------------

    def _load_config(self):
        if self._config_path.exists():
            try:
                with open(self._config_path) as f:
                    self._config = json.load(f)
            except Exception:
                pass

    def _save_config(self):
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w") as f:
            json.dump(self._config, f, indent=2)

    def is_enabled(self, instance_name: str) -> bool:
        """Check if a hook instance is enabled."""
        if instance_name in self._config.get("enabled", []):
            return True
        if instance_name in self._config.get("disabled", []):
            return False
        inst = self._instances.get(instance_name)
        if inst and inst.enabled_by_default:
            return True
        return False

    def enable(self, instance_name: str) -> bool:
        if instance_name not in self._instances:
            return False
        enabled = self._config.setdefault("enabled", [])
        disabled = self._config.setdefault("disabled", [])
        if instance_name not in enabled:
            enabled.append(instance_name)
        if instance_name in disabled:
            disabled.remove(instance_name)
        self._save_config()
        return True

    def disable(self, instance_name: str) -> bool:
        if instance_name not in self._instances:
            return False
        enabled = self._config.setdefault("enabled", [])
        disabled = self._config.setdefault("disabled", [])
        if instance_name in enabled:
            enabled.remove(instance_name)
        if instance_name not in disabled:
            disabled.append(instance_name)
        self._save_config()
        return True

    # ------------------------------------------------------------------
    # Fire
    # ------------------------------------------------------------------

    def fire(self, event_name: str, **kwargs) -> List[Any]:
        """Fire all enabled instances registered for this event.

        Returns a list of results from each handler.
        """
        results = []
        for inst_name, inst in self._instances.items():
            if inst.event_name != event_name:
                continue
            if not self.is_enabled(inst_name):
                continue
            try:
                r = inst.execute(**kwargs)
                results.append({"instance": inst_name, "ok": True, "result": r})
            except Exception as e:
                results.append({"instance": inst_name, "ok": False, "error": str(e)})
        return results

    # ------------------------------------------------------------------
    # Introspection (for CLI)
    # ------------------------------------------------------------------

    def list_interfaces(self) -> List[Dict[str, str]]:
        out = []
        for name, iface in sorted(self._interfaces.items()):
            out.append({
                "event_name": iface.event_name,
                "description": iface.description,
            })
        return out

    def list_instances(self) -> List[Dict[str, Any]]:
        out = []
        for name, inst in sorted(self._instances.items()):
            out.append({
                "name": inst.name,
                "event_name": inst.event_name,
                "description": inst.description,
                "enabled": self.is_enabled(name),
                "enabled_by_default": inst.enabled_by_default,
            })
        return out

    def get_instance_info(self, name: str) -> Optional[Dict[str, Any]]:
        inst = self._instances.get(name)
        if not inst:
            return None
        return {
            "name": inst.name,
            "event_name": inst.event_name,
            "description": inst.description,
            "enabled": self.is_enabled(name),
            "enabled_by_default": inst.enabled_by_default,
            "module_file": str(self._find_instance_file(name) or ""),
        }

    def _find_instance_file(self, name: str) -> Optional[Path]:
        for d in [self._base_hooks_dir / "instance", self.hooks_dir / "instance"]:
            p = d / f"{name}.py"
            if p.exists():
                return p
        return None
