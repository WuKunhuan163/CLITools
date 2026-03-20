---
name: code-quality-review
description: Static analysis and quality auditing for AITerminalTools. Covers dead code detection, unused imports/variables, syntax errors, import rules (IMP001-IMP005), hooks/interface validation, language coverage, and test structure audits.
---

# Code Quality Review

## Dead Code & Static Analysis

The `TOOL --audit code` command runs automated checks via ruff and vulture:

| Check | Description |
|-------|-------------|
| Unused imports (F401) | `import X` where X is never referenced |
| Unused variables (F841) | Local variables assigned but never read |
| Syntax errors (E9) | Invalid Python syntax, indentation errors |

```bash
TOOL --audit code                  # Full scan of logic/, tool/, interface/
TOOL --audit code --fix            # Auto-fix safe issues (unused imports/variables)
TOOL --audit code --targets tool/  # Scan specific directory
```

Programmatic access:

```python
from interface.audit import run_full_audit, print_report

report = run_full_audit(auto_fix=True)
print_report(report)
```

Implementation: `logic/audit/code_quality.py`

## Import Rules

### The Three Valid Import Patterns

Only these patterns are allowed:

1. **Same-directory imports** — code inside `logic/` calling other `logic/` modules, or `tool/X/logic/` calling its own submodules.
2. **Interface imports** — any code outside `logic/` or `interface/` must import through `interface/*`.
3. **Interface bridge imports** — `interface/*.py` files import from `logic.*` to re-export.

Everything else is a violation.

### Rules

The `TOOL --audit imports` command checks five rules:

| Rule | Severity | Description |
|------|----------|-------------|
| IMP001 | ERROR | Cross-tool imports MUST use `tool.X.interface.main`, never `tool.X.logic` |
| IMP002 | ERROR | Raw CDP tab operations (`find_tab`, `open_tab`, `list_tabs`) should use CDMCP `session.require_tab()` |
| IMP003 | ERROR | Hardcoded CDMCP paths — use `interface.cdmcp` loaders |
| IMP004 | WARNING | `ToolBase` used with Chrome/CDP — MCP tools should use `MCPToolBase` from `interface.tool` |
| IMP005 | ERROR | Entry point files (`main.py`, `setup.py`, `hooks/`) import from `logic.*` — must use `interface.*` |

### Available Interface Modules

| Interface | Exposes |
|-----------|---------|
| `interface.tool` | `ToolBase`, `MCPToolBase`, `ToolEngine` |
| `interface.config` | `get_color`, `get_setting`, `get_global_config`, `set_global_config`, `generate_ai_rule`, `inject_rule` |
| `interface.turing` | `TuringStage`, `ProgressTuringMachine`, `TuringWorker`, `MultiLineManager` |
| `interface.hooks` | `HookInstance`, `HookInterface` |
| `interface.chrome` | `CDPSession`, `CDP_PORT`, `is_chrome_cdp_available`, `list_tabs`, etc. |
| `interface.cdmcp` | `load_cdmcp_sessions`, `load_cdmcp_overlay`, `load_cdmcp_interact` |
| `interface.mcp` | `MCPToolConfig`, `is_cursor_environment` |
| `interface.resolve` | `setup_paths` |
| `interface.utils` | `suggest_commands`, `format_table`, `print_success_status`, `cleanup_old_files`, etc. |
| `interface.lang` | `get_translation`, `audit_lang`, `list_languages` |
| `interface.gui` | GUI environment setup, window base classes |
| `interface.audit` | All audit functions (code quality, imports, hooks) |
| `interface.search` | `search_tools`, `search_interfaces`, `search_skills`, `search_tools_deep` |
| `interface.dev` | `dev_create`, `dev_sync`, `dev_audit_test`, etc. |
| `interface.lifecycle` | `list_tools`, `install_tool`, `uninstall_tool` |
| `interface.git` | `install_hooks`, `uninstall_hooks`, `get_persistence_manager` |
| `interface.accessibility` | `check_accessibility_trusted`, `request_accessibility_permission` |

### Checking Imports

```bash
TOOL --audit imports                    # Check all tools + root files
TOOL --audit imports --tool GOOGLE      # Check specific tool
TOOL --audit imports --docs             # Also audit documentation examples
TOOL --audit imports --json             # Machine-readable output
```

### Fixing Violations

When violations are found, write a temporary batch script (`tmp/fix_*.py`) that:
1. Reads each violating file
2. Replaces `from logic.X import Y` with the corresponding `from interface.X import Y`
3. Prints each change for verification
4. If an interface module doesn't exist yet, create it in `interface/` first

## Hooks & Interface Validation

Every tool exposing cross-tool functionality must have:
- `interface/main.py` with explicit re-exports
- Documented public API in module docstring

```bash
TOOL --dev sanity-check <NAME>           # Validates tool structure
TOOL --dev sanity-check <NAME> --fix     # Auto-creates missing files
```

## Language Coverage Audit

```bash
TOOL lang audit                    # Check translation coverage for all tools
TOOL lang audit --tool <NAME>      # Single tool
TOOL lang audit --turing           # With Turing Machine display
```

Translation rules:
- Every user-facing string must use `_("key", "Default text")`
- No `en.json` file -- English is the code default
- Missing translations fall back to English gracefully

## Test Structure Audit

```bash
TOOL --dev audit-test <NAME>           # Check test file naming
TOOL --dev audit-test <NAME> --fix     # Auto-rename files
```

Rules:
- Files must match `test_XX_name.py` pattern (two-digit index)
- `test_00_help.py` is mandatory
- See `unit-test-conventions` for full details

## Agent Development Workflow

When developing OPENCLAW agent features or any tool logic, periodically run:

```bash
TOOL --audit code --targets tool/OPENCLAW/  # Check specific tool
TOOL --audit code                            # Check entire project
TOOL --audit code --fix                      # Auto-fix safe issues
```

Integrate these checks into your development loop:
1. **Before committing**: `TOOL --audit code` to catch regressions
2. **After refactoring**: `TOOL --audit code --fix` to clean up dead imports
3. **When reviewing**: Check `logic/audit/code_quality.py` for programmatic access
