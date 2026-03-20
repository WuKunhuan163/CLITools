# USERINPUT Logic — Technical Reference

## Architecture

USERINPUT's CLI is decomposed into hierarchical modules. `main.py` is a thin router; each subcommand lives in its own directory with `cli.py` and `argparse.json`.

### Module Map

| Module | Responsibility |
|--------|---------------|
| `__init__.py` | Shared utilities (get_config, get_msg, exceptions, set_tool) |
| `cli.py` | Default entry: GUI feedback collection, output formatting, retry loop |
| `queue/store.py` | Queue FIFO storage (read/write `queue.json`) |
| `queue/cli.py` | `--queue` subcommand dispatch |
| `prompt/cli.py` | `--system-prompt` subcommand dispatch |
| `config/cli.py` | `--config` + `--enquiry-mode` dispatch |
| `prompts.py` | Default system prompt templates (UNIVERSAL, PROJECT, IDE) |

### Data Files

| File | Format | Managed by |
|------|--------|-----------|
| `config.json` | `{focus_interval, time_increment, system_prompt, ...}` | config/cli.py, prompt/cli.py |
| `queue.json` | `{"prompts": ["text1", ...]}` | queue/store.py |

### Shared Utilities (`__init__.py`)

- `set_tool(tool)` — Register UserInputTool instance (call from main.py)
- `get_config()` / `save_config(config)` — Read/write config.json
- `get_msg(key, default)` — i18n translation via registered tool
- `get_cursor_session_title()` — Session title for GUI window
- `parse_gui_error()` — Filter Tkinter/macOS noise from error output
- `reorder_list(items, idx, dir)` — In-place list reordering
- `UserInputRetryableError`, `UserInputFatalError` — Exception classes

### argparse.json Convention

Each directory has `argparse.json` describing its commands. The `---help` eco command (`logic/_/help/cli.py`) can read these to generate a hierarchical help tree. Tool-level help extends this pattern beyond eco commands.

## Gotchas

1. **queue.json location**: In `logic/` (transient code data), not `data/` (persistent user data). Intentional.
2. **Blocking command**: USERINPUT is blocking. Never background it.
3. **set_tool() required**: `get_msg()` returns English defaults until `set_tool()` registers the UserInputTool instance. `main.py` calls this immediately after creating the tool.
4. **queue/store.py path**: References `../queue.json` (parent directory) since store.py moved into the `queue/` package.
