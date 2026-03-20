# GOOGLE.GDS Logic — Technical Reference

## Architecture

GDS operates as a Google Drive Shell: commands are translated into operations
against the Google Drive API via service account credentials.

> **Note**: The original architecture also included CDP/Colab browser automation
> paths. These have been disabled due to ToS concerns. The Google Drive API
> path remains fully functional.

```
CLI command -> command/<name>.py -> executor.py -> Google Drive API -> result
```

## Key Classes

### GDSStateManager (`state.py`)
Manages persistent shell state in `data/shell_state.json`:
- `cwd`: Current remote working directory
- `shell_type`: bash or python
- `history`: Command history

### ReconnectionManager (`reconnection_manager.py`)
Auto-triggers Drive remount when:
- Command count exceeds 50 (configurable)
- A single command exceeds 300s (configurable)
Uses lock files under `data/run/` for coordination.

## Command Module Pattern

Each command in `command/` follows the signature:
```python
def execute(tool, args, state_mgr, load_logic, **kwargs):
    """
    tool: ToolBase instance
    args: parsed argparse Namespace
    state_mgr: GDSStateManager
    load_logic: function to dynamically load other command modules
    """
```

### Command Inventory
| Command | File | Purpose |
|---------|------|---------|
| ls | `ls.py` | List remote directory |
| cd | `cd.py` | Change remote directory |
| cat | `cat.py` | Display file content |
| read | `read.py` | Display with line numbers |
| grep | `grep.py` | Pattern search in files |
| edit | `edit.py` | Edit remote files via base64 Python scripts |
| upload | `upload.py` | Upload local -> Drive (size-based strategy) |
| bg | `bg.py` | Background remote execution with status tracking |
| raw_cmd | `raw_cmd.py` | Real-time output from Colab |
| shell | `shell.py` | Interactive REPL |
| pwd | `pwd.py` | Print working directory |
| venv | `venv.py` | Remote Python venv management |
| linter | `linter.py` | Lint remote files locally |
| remount_cmd | `remount_cmd.py` | Drive remount via GUI |
| gui_queue | `gui_queue.py` | FIFO queue for GUI interaction windows |
| tutorial_cmd | `tutorial_cmd.py` | Redirect → `tutorial/src/tutorial_cmd.py` |

## MCP Module (`mcp/`) — DISABLED (ToS Risk)
CDP-based automation for Colab notebooks. **All functionality disabled** due to
potential violation of Google Colab's Terms of Service (automated web UI interaction).
Code preserved for reference:
- `cdp_boot.py`: Chrome session bootstrap for GDS
- `create.py`: Create new Colab notebooks
- `execute.py`: Execute cells in Colab

## Tutorial System (`tutorial/`)
Two guided setup flows:
- `setup_guide/` (6 steps): Full GDS setup including Google Cloud Console, service account, API key, folder configuration
- `mcp_setup/` (4 steps): MCP-specific setup

## Gotchas

1. **IPv4 forced** in `auth.py`: macOS IPv6 can hang for 60s on googleapis.com. The code force-patches urllib3 to use IPv4.
2. **config.json at project root**: GDS stores `root_folder_id`, `env_folder_id`, `mount_hash` in the project-level `data/config.json`, not tool-level.
3. **Tutorial cache**: Tutorial step_04 stores service account key cache in `tool/GOOGLE.GDS/data/tutorial/cache/` (moved from project-level `data/tutorial/cache/`).
