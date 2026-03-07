# interface/ — Technical Reference

## Purpose

Stable facade layer for cross-tool imports. **All tools MUST import from `interface.*`** instead of reaching into `logic.*` internals. Direct `logic.*` imports are reserved for code inside `logic/` itself.

## Module Map

| Module | Re-exports from | Key symbols |
|--------|----------------|-------------|
| `config` | `logic.config` | `get_color()`, `get_setting()`, `get_global_config()` |
| `gui` | `logic.gui.*` | `ButtonBarWindow`, `TutorialWindow`, `BaseGUIWindow`, `TwoStepLoginWindow`, `TwoFactorAuthWindow`, `EditableListWindow`, `BottomBarWindow` |
| `lang` | `logic.lang.utils` | `get_translation()` |
| `tool` | `logic.tool.*` | `ToolBase`, `MCPToolBase`, `ToolEngine` |
| `turing` | `logic.turing.*` | `ProgressTuringMachine`, `TuringStage`, `TuringWorker`, `ParallelWorkerPool`, `MultiLineManager` |
| `utils` | `logic.utils.*` | `preflight()`, `retry()`, `cleanup_old_files()`, `suggest_commands()`, `SessionLogger`, `get_current_timezone()` |
| `status` | `logic.turing.status` | `fmt_status()`, `fmt_detail()`, `fmt_stage()`, `fmt_warning()`, `fmt_info()` |
| `audit` | `logic.audit.*` | `run_full_audit()`, `print_report()`, `AuditReport`, `Finding` |
| `registry` | Dynamic loader | `get_tool_interface(name)`, `list_tool_interfaces()` |

## Usage Pattern

```python
from interface.config import get_color
from interface.gui import TutorialWindow, TutorialStep
from interface.turing import TuringStage, ProgressTuringMachine
from interface.tool import ToolBase
from interface.utils import preflight, retry, cleanup_old_files
from interface.status import fmt_status, fmt_warning, fmt_info
from interface.audit import run_full_audit, print_report
```

## Tool Interface Registry

Each tool can expose a public API at `tool/<NAME>/interface/main.py`. The registry dynamically loads these:

```python
from interface.registry import get_tool_interface
gcs = get_tool_interface("GOOGLE.GCS")
if gcs:
    gcs.some_function()
```

Loaded modules are cached. Only use this for cross-tool communication — never import another tool's `logic/` directly.

## Gotchas

1. **Import order**: `interface` modules import from `logic.*`. If `logic/` isn't on `sys.path`, imports fail. Always call `setup_paths(__file__)` before importing from `interface`.
2. **No circular imports**: Interface modules must not import from each other.
3. **Registry vs facade**: Use facade modules (`interface.config`, `interface.gui`, etc.) for well-known symbols. Use `registry` for dynamic tool-to-tool communication.
