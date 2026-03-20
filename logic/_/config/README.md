# logic/config

Configuration management for AITerminalTools: global settings, colors, tool-specific config, and rule generation.

## Contents

- **main.py** - Core config access: `get_setting`, `get_global_config`, `set_global_config`, `get_color`, `PROJECT_ROOT`
- **manager.py** - Terminal width check display and `print_width_check`
- **tool_config_manager.py** - `ToolConfigManager` for per-tool config (dot notation, `data/config/config.json`)
- **rule/** - AI rule generation and injection into `.cursor/rules/`
- **colors.json** - ANSI color codes (GREEN, RED, BOLD, etc.)
- **settings.json** - Framework defaults (test concurrency, Python version, etc.)

## Structure

```
config/
  __init__.py
  main.py
  manager.py
  tool_config_manager.py
  colors.json
  settings.json
  rule/
    __init__.py
    manager.py
```
