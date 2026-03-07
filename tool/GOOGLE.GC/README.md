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

### Cell Focus & Context Menu
```bash
GOOGLE.GC cell focus --index 0                            # Focus a cell
GOOGLE.GC cell focus --index 0 --toolbar-click move-up    # Focus + toolbar button
GOOGLE.GC cell focus --index 0 --toolbar-click more       # Open "More actions" menu
GOOGLE.GC cell focus --index 0 --menu-click copy          # Click a More actions item
GOOGLE.GC cell focus --index 0 --menu-click delete        # Delete via context menu
```

Toolbar buttons: `move-up`, `move-down`, `delete`, `edit`, `more`
More actions: `select`, `copy-link`, `cut`, `copy`, `delete`, `comment`, `editor-settings`, `mirror`, `scratch`, `form`

### Toolbar
```bash
GOOGLE.GC toolbar commands       # Open command palette
GOOGLE.GC toolbar add-code       # Add code cell
GOOGLE.GC toolbar add-text       # Add text cell
GOOGLE.GC toolbar run-all        # Run all cells
GOOGLE.GC toolbar run-dropdown   # Run options dropdown
GOOGLE.GC toolbar connect        # Connect/reconnect runtime
GOOGLE.GC toolbar settings       # Open settings dialog
GOOGLE.GC toolbar comments       # Toggle comments pane
GOOGLE.GC toolbar toggle-header  # Toggle top header visibility
```

### Top Bar Menus
```bash
GOOGLE.GC menu file                        # Open File menu
GOOGLE.GC menu runtime --item "Run all"    # Open Runtime menu and click "Run all"
GOOGLE.GC menu tools --item "Settings"     # Open Tools menu and click "Settings"
```

Menus: `file`, `edit`, `view`, `insert`, `runtime`, `tools`, `help`

### Sidebar
```bash
GOOGLE.GC sidebar toc            # Toggle Table of Contents
GOOGLE.GC sidebar find           # Toggle Find and Replace
GOOGLE.GC sidebar snippets       # Toggle Code Snippets
GOOGLE.GC sidebar inspector      # Toggle Data Inspector
GOOGLE.GC sidebar secrets        # Toggle Secrets
GOOGLE.GC sidebar files          # Toggle Files
GOOGLE.GC sidebar data-explorer  # Toggle Data Explorer
```

### Bottom Bar
```bash
GOOGLE.GC bottom variables       # Toggle Variables panel
GOOGLE.GC bottom terminal        # Toggle Terminal panel
```

### Settings Dialog
```bash
GOOGLE.GC settings show                                    # Show current tab settings
GOOGLE.GC settings show --tab Editor                       # Show editor settings
GOOGLE.GC settings set --tab Editor --pref pref_showLineNumbers  # Toggle checkbox
GOOGLE.GC settings set --tab Site --pref pref_siteTheme --value dark  # Set select
GOOGLE.GC settings save                                    # Save and close
GOOGLE.GC settings cancel                                  # Close without saving
```

### State & Other
```bash
GOOGLE.GC state                   # Show MCP state report
GOOGLE.GC state --json            # JSON output for programmatic use
GOOGLE.GC status                  # Check CDP and Colab tab availability
GOOGLE.GC inject "print('hi')" --timeout 30  # Inject and run code directly
GOOGLE.GC reopen                  # Reopen the configured Colab notebook tab
GOOGLE.GC oauth                   # Handle OAuth dialog if present
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
