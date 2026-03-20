# logic/tool — Agent Reference

## Package Layout

```
logic/tool/
├── __init__.py      # empty
├── blueprint/       # ToolBase, MCPToolBase — canonical base classes
│   ├── base.py      # ToolBase
│   └── mcp_base.py  # MCPToolBase
└── template/        # README template for TOOL --dev create
```

## Importing ToolBase

Tools should import via the facade:
```python
from interface.tool import ToolBase, MCPToolBase
```

Internal (inside `logic/`) imports:
```python
from logic.base.blueprint.base import ToolBase
from logic.base.blueprint.mcp_base import MCPToolBase
```

## What Was Moved

These packages were refactored out of `logic/tool/` to `logic/` root:
- `logic.hooks` (was `logic.tool.hooks`) — HooksEngine, base events
- `logic.setup` (was `logic.tool.setup`) — ToolEngine
- `logic.dev` (was `logic.tool.dev`) — dev commands
- `logic.audit` (was `logic.tool.audit`) — quality auditors
- `logic.lifecycle` (was `logic.base.lifecycle`) — install/uninstall/list

All imports project-wide now use the canonical `logic.<module>` paths. No backward-compatibility shims remain.

## Gotchas

- **Do not import from `logic.tool.base`** — that file was removed. Import from `logic.base.blueprint.base`.
- `template/` contains static README template text, not programmatically imported.
