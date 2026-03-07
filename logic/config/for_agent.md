# logic/config - Agent Reference

## Key Interfaces

### main.py
- `get_setting(key, default=None)` - Read from `logic/config/settings.json`
- `get_global_config(key=None, default=None)` - Read from `data/config.json`; omit key for full dict
- `set_global_config(key, value)` - Write to `data/config.json`
- `get_color(color_name, default="\033[0m")` - ANSI code from `colors.json`
- `PROJECT_ROOT` - Path to project root (3 levels up from this file)

### ToolConfigManager (tool_config_manager.py)
- `__init__(tool_name, tool_script_dir)` - Config stored at `tool_script_dir/data/config/config.json`
- `get(key, default)` - Dot notation: `get("foo.bar")`
- `set(key, value)` - Dot notation; auto-creates nested dicts
- `delete(key)` - Dot notation

### config/rule/manager.py
- `generate_ai_rule(project_root, target_tool=None, translation_func=None)` - Prints AI agent rules; on macOS copies to clipboard
- `inject_rule(project_root, translation_func=None)` - Writes rules to `.cursor/rules/AITerminalTools.mdc` (alwaysApply: true)

## Usage Patterns

1. **Colors**: Always use `get_color("BOLD", "\033[1m")` etc. for consistency.
2. **Tool config**: Use `ToolConfigManager` for tool-specific persistence; use `get_global_config` for project-wide.
3. **Rule injection**: Call `inject_rule(project_root)` after tool changes to update Cursor rules.

## Gotchas

- `manager.py` contains both `print_width_check` (terminal width display) and orphaned class-like code; the actual tool config class is in `tool_config_manager.py`.
- `get_global_config` returns `{}` when key is None and file missing; `get_setting` returns default on any error.
