# GOOGLE.GC

Google Colab automation via Chrome DevTools Protocol (CDP) with MCP visual effects.

## Commands

### Cell Management
```bash
GOOGLE.GC cell add                              # Add empty code cell
GOOGLE.GC cell add --text "print('hi')"         # Add code cell with content
GOOGLE.GC cell add --cell-type text --text "# Heading"  # Add text/markdown cell
GOOGLE.GC cell edit --index 0 --clear           # Clear cell content
GOOGLE.GC cell edit --index 0 --type "x = 1"    # Type text at end (char-by-char)
GOOGLE.GC cell edit --index 0 --clear-line 2    # Clear specific line (0-based)
GOOGLE.GC cell edit --index 0 --line 1 --insert "new code"  # Insert at line
GOOGLE.GC cell edit --index 0 --from-line 0 --to-line 2 --replace-with "new\ncontent"
GOOGLE.GC cell delete --index 0                 # Delete specific cell
GOOGLE.GC cell delete                           # Delete last cell
GOOGLE.GC cell move --index 0 --direction down  # Move cell down
GOOGLE.GC cell move --index 1 --direction up    # Move cell up
GOOGLE.GC cell run --index 0                    # Execute cell and wait
GOOGLE.GC cell run --index 0 --wait 60          # Custom timeout
```

### Runtime Control
```bash
GOOGLE.GC runtime run-all       # Run all cells
GOOGLE.GC runtime interrupt     # Interrupt execution
GOOGLE.GC runtime restart       # Restart runtime session
```

### Notebook Operations
```bash
GOOGLE.GC notebook save           # Save notebook (Cmd+S)
GOOGLE.GC notebook clear-outputs  # Clear all cell outputs
```

### Other Commands
```bash
GOOGLE.GC status              # Check CDP and Colab tab availability
GOOGLE.GC inject "print('hi')" --timeout 30  # Inject and run code directly
GOOGLE.GC reopen              # Reopen the configured Colab notebook tab
GOOGLE.GC oauth               # Handle OAuth dialog if present
```

## MCP Visual Effects

All cell and runtime operations include visual feedback:
- **Lock overlay**: Tab is locked during operations (shows "Locked by GC")
- **Badge**: "GC [colab]" badge in top-right corner
- **Focus border**: Orange border indicating agent attention
- **Element highlight**: Targets highlighted with labels before action
- **MCP counter**: Bottom-left timer tracks operations count

## Turing Machine Architecture

Each operation uses a multi-stage Turing machine:
1. `connect` — Verify Chrome CDP availability, load CDMCP modules
2. `find_tab` — Find/open Colab tab via CDMCP `require_tab` (auto-recovery)
3. `<action>` — Perform the operation with visual effects
4. `cleanup` — Remove overlays, close CDP connection

Error states are properly reported (e.g., cell not found, line out of range).

## Tab Lifecycle (CDMCP Integration)

Uses `session_mgr.require_tab()` for tab management:
- If the Colab tab exists in the current session, reuses it
- If missing, auto-opens it in the session window
- If the session window is lost, triggers full session reboot

## Interface

```python
from tool.GOOGLE.logic.chrome.colab import (
    find_colab_tab, reopen_colab_tab, inject_and_execute,
)
from tool.GOOGLE.logic.chrome.oauth import (
    handle_oauth_if_needed, close_oauth_tabs,
)
```

## Dependencies

- **GOOGLE**: Core CDP session management and Chrome automation
- **GOOGLE.CDMCP**: Visual overlays, session management, MCP interaction interfaces
- **GOOGLE.GD**: Google Drive file operations (notebook creation/repair)
- **PYTHON**: Managed Python runtime
