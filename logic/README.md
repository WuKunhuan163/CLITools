# logic/

Shared core logic for the AITerminalTools framework. Every sub-package here is used across multiple tools — tool-specific logic belongs in `tool/<NAME>/logic/` instead.

## Package Index

### Core Infrastructure
| Package | Purpose | Key Exports |
|---------|---------|-------------|
| `tool/` | Tool base classes (blueprint, template) | `ToolBase`, `MCPToolBase` |
| `hooks/` | Event-driven hook system | `HooksEngine`, `HookInterface`, `HookInstance` |
| `setup/` | Tool installation and dependency resolution | `ToolEngine` |
| `lifecycle.py` | Tool install/uninstall/list | `install_tool()`, `list_tools()` |
| `config/` | Global configuration, colors, rule generation | `get_global_config()`, `RuleManager`, `colors.json` |
| `gui/` | GUI framework — Tkinter blueprints, widgets, style | `BaseGUIWindow`, `TimedBottomBarGUI`, `TutorialWindow` |

### Development & Testing
| Package | Purpose | Key Exports |
|---------|---------|-------------|
| `test/` | Test runner with CPU monitoring, parallel execution | `TestManager`, `TestRunner` |
| `dev/` | Developer workflow commands | `dev_sync`, `dev_create`, `dev_audit_test` |
| `audit/` | Quality auditing (hooks, interfaces, skills) | `audit_all_quality`, `AuditManager` |
| `lang/` | Internationalization, language audit | `LangAuditor`, `_()` helper via tools |

### Display & UX
| Package | Purpose | Key Exports |
|---------|---------|-------------|
| `turing/` | Progress display (Turing Machine stages) | `TuringStage`, `ProgressTuringMachine`, `MultiLineManager` |
| `utils/` | Display tables, logging, progress bars | `display_table()`, `save_list_report()`, `system_log()` |
| `accessibility/` | Keyboard monitoring, paste-and-enter | `KeyboardMonitor`, `detect_paste_then_enter()` |
| `terminal/` | Terminal keyboard control (shim to `turing/terminal/`) | `KeyboardSuppressor` |

### Chrome DevTools / MCP
| Package | Purpose | Key Exports |
|---------|---------|-------------|
| `chrome/` | Chrome session management | `CDPSession`, `list_tabs()`, `find_tab()` |
| `mcp/` | MCP infrastructure (browser config, Drive) | `load_browser_config()` |
| `cdmcp_loader.py` | CDMCP session bootstrapper (top-level file) | `boot_tool_session()` |

### Data & Assets
| Package | Purpose | Key Exports |
|---------|---------|-------------|
| `git/` | Git operations, .gitignore management | `GitIgnoreManager`, `GitPersistenceManager` |
| `asset/` | Static assets (notification sounds) | `bell.mp3` |
| `translation/` | Root translation files | `zh.json`, `ar.json` |

## Top-Level Files

| File | Purpose |
|------|---------|
| `resolve.py` | Universal `sys.path` resolver — ensures project root is at `sys.path[0]` |
| `cdmcp_loader.py` | CDMCP session bootstrap for Chrome-based tools |
| `lifecycle.py` | Tool install/uninstall/list commands |
| `worker.py` | Background worker/process utilities |
| `__init__.py` | Package marker |

## Import Convention

```python
from logic.config.main import get_global_config
from logic.tool.blueprint.base import ToolBase
from logic.turing.stage import TuringStage
```

Each sub-package has its own `README.md` (overview) and `for_agent.md` (technical detail).
