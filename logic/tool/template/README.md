# logic/tool/template

Scaffold templates for `TOOL --dev create <NAME>`. Each `.tmpl` file is loaded by `logic.dev.commands.dev_create()` and filled with `{name}` and `{short_name}` placeholders.

## Template Files

| File | Generated As |
|------|-------------|
| `main.py.tmpl` | `tool/<NAME>/main.py` |
| `setup.py.tmpl` | `tool/<NAME>/setup.py` |
| `tool.json.tmpl` | `tool/<NAME>/tool.json` |
| `test_00_help.py.tmpl` | `tool/<NAME>/test/test_00_help.py` |
| `test_01_basic.py.tmpl` | `tool/<NAME>/test/test_01_basic.py` |
| `interface_main.py.tmpl` | `tool/<NAME>/interface/main.py` |
| `hook_interface.py.tmpl` | `tool/<NAME>/hooks/interface/on_demo_action.py` |
| `hook_instance.py.tmpl` | `tool/<NAME>/hooks/instance/demo_logger.py` |
| `for_agent.md.tmpl` | `tool/<NAME>/for_agent.md` |
| `tool_readme.md.tmpl` | `tool/<NAME>/README.md` |

## Generated Directories

| Directory | Purpose |
|-----------|---------|
| `logic/` | Internal implementation |
| `interface/` | Public API facade |
| `hooks/` | Hook entry points + implementations |
| `eco/` | Ecosystem navigation data |
| `test/` | Unit tests |
| `report/` | Development reports |

## Placeholders

- `{name}` — full tool name (e.g. `GOOGLE.GDS`)
- `{short_name}` — last segment for CLI (e.g. `GDS`)
