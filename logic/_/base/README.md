# logic/tool

Tool blueprint and template — the core building blocks for creating new AITerminalTools tools.

## Purpose

Provides `ToolBase` and `MCPToolBase` base classes that all tools inherit from, plus the `template/` directory used by `TOOL --dev create` to scaffold new tools.

## Structure

| Path | Responsibility |
|------|----------------|
| blueprint/ | ToolBase, MCPToolBase — canonical base classes |
| template/ | README template for `TOOL --dev create` |

## Related Packages (now at logic/ root)

The following were previously in `logic/tool/` and have been moved:
- `logic/hooks/` — HooksEngine, HookInterface, HookInstance
- `logic/setup/` — ToolEngine (install/uninstall)
- `logic/dev/` — dev_sanity_check, dev_audit_test, dev_create
- `logic/audit/` — Quality auditors (hooks, interfaces, skills)
- `logic/lifecycle.py` — install_tool, reinstall_tool, uninstall_tool, list_tools
