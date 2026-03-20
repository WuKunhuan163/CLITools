# interface/

Public facade layer. **All tools MUST import shared utilities from `interface.*`**, not directly from `logic.*`. The `interface/` modules re-export stable symbols from `logic/` internals, providing a clean API boundary.

This directory is auto-tracked in `.gitignore` via `GitIgnoreManager.base_patterns` (see `logic/_/git/manager.py`).

## Modules

- `config.py` — Color and style configuration (`get_color()`).
- `gui.py` — GUI style helpers.
- `lang.py` — Translation/localization helpers.
- `registry.py` — Tool registry and discovery.
- `tool.py` — Cross-tool invocation interface.
- `turing.py` — Turing Machine progress display interface.
- `utils.py` — Shared utilities: preflight, retry, cleanup, fuzzy, display, timezone, system.
- `status.py` — Terminal status formatters: `fmt_status()`, `fmt_warning()`, `fmt_info()`.
- `audit.py` — Code quality auditing: `run_full_audit()`, `print_report()`.

## Usage

```python
from interface.config import get_color
from interface.lang import get_translation
from interface.utils import preflight, retry, cleanup_old_files
from interface.status import fmt_status, fmt_warning
from interface.audit import run_full_audit
```

Tools expose their own public API via `tool/<NAME>/interface/main.py`. See `SKILLS show tool-interface` for the full pattern.
