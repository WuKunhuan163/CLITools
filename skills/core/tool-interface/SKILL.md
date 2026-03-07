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
4. Document every public function with a docstring (see standard below)
5. Before creating a new interface, search for existing ones:
   ```bash
   TOOL --search interfaces "what you need"
   ```

```python
"""MY_TOOL Interface -- public API for cross-tool access.

Usage::
    from tool.MY_TOOL.interface.main import my_function
"""
from tool.MY_TOOL.logic.core import my_function  # noqa: F401
```

## Interface Docstring Standard

Every function exported through an interface MUST have a docstring following
this format.  This enables semantic search and helps agents discover the
right interface quickly.

```python
def get_system_git() -> str:
    """Resolve the real system ``git`` binary, bypassing any PATH shadows.

    On macOS, ``bin/GIT/`` in PATH can shadow ``/usr/bin/git`` due to
    case-insensitive APFS.  This function searches PATH with project
    ``bin/`` directories excluded, falling back to well-known locations.

    Returns
    -------
    str
        Absolute path to the system git binary.
    """
```

### Rules

1. **First line**: One-sentence summary of what the function does. Use imperative
   mood ("Resolve ...", "Send ...", "Build ...").
2. **Body** (optional): Extended description with context, edge cases, or
   constraints.  Wrap at 72 characters.
3. **Parameters**: Use NumPy-style ``Parameters`` section with type annotations.
   ```
   Parameters
   ----------
   name : str
       Description of the parameter.
   count : int, optional
       Default is 10.
   ```
4. **Returns**: Use NumPy-style ``Returns`` section.
   ```
   Returns
   -------
   list[dict]
       Each dict has ``id``, ``score``, ``meta`` keys.
   ```
5. **Raises** (if applicable): Document expected exceptions.
6. **Examples** (optional): Show usage in a ``>>>`` block for complex APIs.

### Searching Interfaces

Agents should search for existing interfaces before writing new code:

```bash
# Natural language search
TOOL --search interfaces "run a git command"
TOOL --search interfaces "manage background processes"

# Then read the matched interface file for full API details
```

## Path Resolution

Always ensure `logic.resolve.setup_paths()` has been called before cross-tool imports. In ToolBase-managed code, this is automatic. In standalone scripts, use the bootstrap preamble.
