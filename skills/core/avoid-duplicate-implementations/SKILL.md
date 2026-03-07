---
name: avoid-duplicate-implementations
description: Guide for avoiding duplicate implementations when adding new features or patterns to the codebase.
---

# Avoid Duplicate Implementations

## Core Rule

Before implementing any new functionality, search for existing code that does something similar. Extend or refactor existing code instead of writing parallel implementations.

## Search Checklist

1. **Grep for function/class names** related to your feature
2. **Check `interface/main.py`** files for already-exposed APIs
3. **Read `for_agent.md`** and `README.md` for documented patterns
4. **Search `skills/`** for relevant conventions
5. **Check `logic/`** for shared utilities
6. **Check `logic/gui/tkinter/blueprint/`** for reusable tkinter GUI components
7. **Check `logic/gui/html/blueprint/`** for reusable HTML/web GUI components (chatbot, etc.)

## Common Duplication Patterns

### Pattern 1: Reimplementing a Utility

Before:
```python
# In tool/MY_TOOL/logic/helpers.py
def read_json_file(path):
    with open(path) as f:
        return json.load(f)
```

Check: Does `logic/utils/` already have this?

### Pattern 2: Parallel API Wrappers

Before creating a new CDP wrapper, check:
- `tool/GOOGLE/logic/chrome/session.py` (CDPSession)
- `tool/GOOGLE.CDMCP/logic/cdp/` (session manager, overlays)
- `tool/GOOGLE/interface/main.py` (public API)

### Pattern 3: Custom GUI Instead of Blueprint

Before building a new tkinter GUI, check `logic/gui/tkinter/blueprint/`:
- `chatbot/` — Multi-session chat with sidebar
- `button_bar/` — Horizontal button row
- `editable_list/` — Reorderable list with CRUD
- `bottom_bar/` — Cancel/Save action bar
- `tutorial/` — Multi-step wizard
- `account_login/` — Login form

All blueprints extend `BaseGUIWindow` and support external control via `cmd_*()` methods and flag-file remote control.

### Pattern 4: Configuration Handling

Use the existing config system (`ToolBase.config`, `tool.json`) rather than custom config parsing.

## When Duplication is Acceptable

- Isolating a prototype in `tmp/` before integrating
- Tool-specific logic that genuinely differs from the shared version
- Performance-critical paths where abstraction adds overhead

## Migration Steps

When you find existing code:
1. Verify it covers your use case (or can be extended)
2. Import via `interface/main.py` (cross-tool) or `logic/` (same tool)
3. If extending, add the new capability to the existing function
4. Update callers to use the unified implementation
5. Remove the duplicate code
