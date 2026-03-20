# Hooks — Agent Reference

## Architecture: Blueprints and Instances

Hooks follow the blueprint-instance pattern:
- **Blueprints** live in `logic/_/` (deep): hook scripts, templates, configuration
- **Instances** are deployed to shallow paths that the IDE/runtime can reference

### IDE Hooks (Cursor)
- **Blueprint**: `logic/_/hooks/IDE/Cursor/` — source scripts + docs
- **Config blueprint**: `logic/_/setup/IDE/cursor/hooks/hooks.json`
- **Deployed instance**: `.cursor/hooks.json` (references blueprint paths)
- **Deploy command**: `TOOL --setup` or `logic/_/setup/IDE/cursor/deploy.py`

### Tool Hooks (internal)
- **Blueprint interfaces**: `<TOOL>/hooks/interface/` — event definitions
- **Blueprint instances**: `<TOOL>/hooks/instance/` — handler scripts
- **Config**: `<TOOL>/hooks/config.json`

## HookInterface

Base for event definitions. Subclass in `<TOOL>/hooks/interface/<event>.py`.
- **event_name**: str (required)
- **description**: str
- **validate_kwargs(kwargs)** — optional validation; default returns True

## HookInstance

Base for handlers. Subclass in `<TOOL>/hooks/instance/<name>.py`.
- **name**: str (required, unique)
- **description**: str
- **event_name**: str (required, must match a HookInterface)
- **enabled_by_default**: bool (default False)
- **execute(**kwargs)** — override; raises NotImplementedError by default

## HooksEngine

### __init__(tool_dir, tool_name="", project_root=None)
Discovers interfaces from logic/tool/hooks/base/interface and tool_dir/hooks/interface. Discovers instances from base/instance and tool_dir/hooks/instance. Loads config from tool_dir/hooks/config.json.

### fire(event_name, **kwargs) -> List[Dict]
Runs all enabled instances for the event. Returns list of `{"instance": name, "ok": bool, "result"|"error": ...}`.

### is_enabled(instance_name), enable(name), disable(name)
Config persistence in config.json: `{"enabled": [...], "disabled": [...]}`.

### list_interfaces(), list_instances(), get_instance_info(name)
For CLI (TOOL hooks list|show|enable|disable).

## Directory Layout

```
logic/_/hooks/
├── engine.py          # Shared hook execution engine
├── base/interface/    # Base hook event definitions (on_tool_start, on_tool_exit)
├── instance/          # Shared hook instances (skills_scan, tmp_cleanup)
├── interface/         # Shared hook interfaces (before/after_tool_call)
└── IDE/
    └── Cursor/        # Cursor-specific hooks (brain_inject, brain_remind, etc.)

<TOOL>/hooks/
├── interface/         # Tool-specific event definitions
├── instance/          # Tool-specific handlers
└── config.json        # {"enabled": [...], "disabled": [...]}
```

## Usage

Tool fires via `self.fire_hook("on_tool_start", tool=self, args=args)`. ToolBase injects `tool=self` automatically.

## Gotchas

- Modules loaded via importlib.util.spec_from_file_location; load failures are silent (mod returns None).
- Config: if instance not in enabled or disabled, enabled_by_default determines state.
- Base interfaces/instances are merged with tool-specific; tool instances override base by name.
- IDE hooks are standalone scripts (not HookInstance subclasses) — they use stdin/stdout JSON protocol per Cursor's hook spec.
