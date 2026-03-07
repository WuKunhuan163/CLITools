---
name: tool-interface
description: Create and use tool interfaces (interface/main.py) for cross-tool communication in AITerminalTools.
---

# Tool Interface Pattern

## Overview

Every tool that exposes functionality to other tools should provide a `interface/main.py` file. This serves as the public API contract.

## Example: Google Tool Hierarchy

```
GOOGLE                          # Infrastructure layer
├── logic/chrome/session.py     # Core CDP session (CDPSession, real_click, etc.)
├── logic/chrome/colab.py       # Colab cell injection (inject_and_execute)
├── logic/chrome/drive.py       # Drive CRUD (list_drive_files, create_notebook)
├── logic/chrome/oauth.py       # OAuth automation (handle_oauth_if_needed)
└── interface/main.py     # Aggregated public API

GOOGLE.GD                       # Drive operations layer
└── interface/main.py     # Re-exports from tool.GOOGLE.logic.chrome.drive

GOOGLE.GC                       # Colab operations layer
└── interface/main.py     # Re-exports from tool.GOOGLE.logic.chrome.colab + oauth

GOOGLE.GCS                      # Simulated shell (highest abstraction)
└── Uses logic/cdp/colab.py     # Backward-compat shim → tool.GOOGLE.logic.chrome
```

## Import Patterns

### Cross-tool import (MUST use interface)
```python
from tool.GOOGLE.interface.main import (
    is_chrome_available, find_colab_tab, inject_and_execute,
    list_drive_files, handle_oauth_if_needed,
)
```

### Internal import (within the same tool only)
```python
# Only allowed inside tool/GOOGLE/ itself:
from tool.GOOGLE.logic.chrome.session import CDPSession, CDP_PORT
from tool.GOOGLE.logic.chrome.colab import inject_and_execute
```

### Direct imports from canonical locations
```python
from logic.chrome.session import CDPSession
from tool.GOOGLE.logic.chrome.colab import find_colab_tab, inject_and_execute
from tool.GOOGLE.logic.chrome.oauth import handle_oauth_if_needed, close_oauth_tabs
```

> **Important**: `logic/` is internal implementation. Cross-tool access MUST go through `interface/main.py`.
> The `TOOL audit imports` command enforces this rule (IMP001).

## Creating an Interface

1. Create `tool/<NAME>/interface/main.py`
2. Import and re-export the public API
3. Use `# noqa: F401` for re-exports
4. Document usage in the module docstring

```python
"""MY_TOOL Interface — description.

Usage::
    from tool.MY_TOOL.interface.main import my_function
"""
from tool.MY_TOOL.logic.core import my_function  # noqa: F401
```

## Path Resolution

Always ensure `logic.resolve.setup_paths()` has been called before cross-tool imports. In ToolBase-managed code, this is automatic. In standalone scripts, use the bootstrap preamble.
