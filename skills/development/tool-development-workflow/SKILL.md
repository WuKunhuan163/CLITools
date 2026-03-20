---
name: tool-development-workflow
description: Complete guide for developing new tools in AITerminalTools, from template creation to testing and deployment.
---

# Tool Development Workflow

## 1. Create a New Tool

```bash
TOOL --dev create <NAME>          # Creates tool/<NAME>/ with all required files
```

This generates: `main.py`, `setup.py`, `tool.json`, `README.md`, `logic/`, `logic/translation/`, `test/test_00_help.py`, `test/test_01_basic.py`.

## 2. Universal Path Resolver Bootstrap

Every tool entry point (`main.py`, `setup.py`) MUST use the resolver preamble:

```python
import sys; from pathlib import Path
_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)
```

This ensures `sys.path[0]` is the project root and prevents import shadowing.

## 3. Tool Structure

```
tool/<NAME>/
├── main.py               # Entry point (ToolBase subclass)
├── setup.py              # Installation logic (ToolEngine)
├── tool.json             # Metadata: name, version, dependencies
├── README.md             # Documentation
├── interface/            # Public API for cross-tool communication
│   └── main.py
├── hooks/                # Event-driven callbacks
│   ├── interface/        # Hook event definitions
│   └── instance/         # Concrete hook implementations
├── logic/                # Internal implementation (not for cross-tool access)
│   └── translation/      # Localization files
│       └── zh.json
└── test/                 # Unit tests
    ├── test_00_help.py
    └── test_01_basic.py
```

## 3b. Dependency Discovery (Before Writing Code)

After creating the tool scaffold, read the `AGENT.md` of every dependency listed in `tool.json`:

```bash
# For each dependency in tool.json:
cat tool/<DEPENDENCY>/AGENT.md       # Tool-specific API and gotchas
cat tool/<DEPENDENCY>/logic/AGENT.md # Internal architecture
```

Key dependency patterns:
- **GOOGLE.CDMCP**: Use `boot_tool_session()` and `ensure_chrome()`. Never manage Chrome manually.
- **GUI components**: Check `logic/gui/tkinter/blueprint/` for existing blueprints before building custom UIs.
- **PYTHON**: Use `get_safe_python_for_gui()` for tkinter subprocess launching.

Also read root-level dependency docs:
- `logic/AGENT.md` — Path resolution, dependency graph, gotchas
- `logic/chrome/AGENT.md` — CDPSession, tab helpers (if Chrome-based)
- `logic/gui/AGENT.md` — GUI patterns, Interface I protocol (if GUI-based)

## 4. ToolBase Features

All tools inherit `handle_command_line(parser, dev_handler, test_handler)`:

- **Automatic commands**: `setup`, `install`, `uninstall`, `rule`, `config`, `skills`
- **`--dev` support**: `sanity-check`, `audit-test`, `info` (built-in for all tools)
- **`--test` support**: Run unit tests with `--range`, `--max`, `--timeout`, `--list`
- **Custom handlers**: Pass `dev_handler` / `test_handler` callbacks for tool-specific commands

## 5. Sub-Tool Naming

Sub-tools use dot-separated names: `PARENT.CHILD` (e.g., `GOOGLE.GDS`).
- Directory: `tool/GOOGLE.GDS/`
- ToolBase name: `ToolBase("GOOGLE.GDS")`
- Shortcut: `bin/GDS/GDS` (uses the last segment)

## 6. Cross-Tool Imports

Cross-tool imports **MUST** go through the tool's `interface/main.py`:
```python
from tool.GOOGLE.interface.main import CDPSession, find_colab_tab
```

Direct access to another tool's `logic/` is forbidden. The `TOOL --audit imports` command (IMP001) enforces this. Internal imports within the same tool can use `logic/` directly.

## 7. Developer Commands

```bash
TOOL_NAME --dev sanity-check [--fix]   # Check structure
TOOL_NAME --dev audit-test [--fix]     # Audit test naming
TOOL_NAME --dev info                   # Show paths & deps
TOOL_NAME --test                       # Run all tests
TOOL_NAME --test --list                # List tests
```

## 8. Testing

- File naming: `test_XX_name.py` (two-digit index)
- `test_00_help.py` is mandatory (tests `--help` flag)
- Run: `TOOL --test <NAME>` or `TOOL_NAME --test`
- Constants: `EXPECTED_TIMEOUT = 300`, `EXPECTED_CPU_LIMIT = 40.0`

## 9. Localization

- English strings as defaults in code: `_("key", "Default text")`
- Translation files in `logic/translation/<lang>.json`
- NO `en.json` — English is always the code default
