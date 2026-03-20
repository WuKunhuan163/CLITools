# GOOGLE.GC -- For Agent Reference

Google Colab automation via CDMCP with MCP visual effects.

## Quick Reference

See `for_agent/commands.md` for complete command reference.
See `for_agent/technical.md` for implementation details.

### Most Used Commands
```bash
GOOGLE.GC cell add --text "print('hello')"       # Add code cell
GOOGLE.GC cell edit --index 0 --clear --type "x=1"  # Clear and type
GOOGLE.GC cell run --index 0                       # Run cell
GOOGLE.GC cell delete --index 0                    # Delete cell
GOOGLE.GC cell focus --index 0 --toolbar-click move-up  # Move cell
GOOGLE.GC toolbar add-code                         # Add code cell via toolbar
GOOGLE.GC menu runtime --item "Run all"            # Click Runtime > Run all
GOOGLE.GC sidebar files                            # Toggle Files panel
GOOGLE.GC bottom terminal                          # Toggle Terminal panel
GOOGLE.GC settings show --tab Editor               # View editor settings
GOOGLE.GC settings set --tab Editor --pref pref_showLineNumbers  # Toggle line numbers
GOOGLE.GC settings save                            # Save settings
GOOGLE.GC state --json                             # Get full state
```

### Key Behaviors
- Uses CDMCP `require_tab()` for tab lifecycle (auto-recovery)
- All operations show MCP visual effects (lock, highlight, counter)
- Turing machine state tracking for error recovery
- Supports all Colab interactive elements: top-bar menus, toolbar, sidebar, cell toolbar, bottom bar, settings dialog

### MCP State (`state --json`)
Returns: `cdp_available`, `colab_tab`, `cells` (index, type, text, focused), `cell_count`, `runtime` (connected, button_text, running_cells, pending_cells), `notebook` (title, url), `sessions` (sessionId, title, fileId, lastActivity, accelerator, visibleInUi).

### Session Management
The `sessions` array in MCP state lists all active Colab runtime sessions via `kernel.listNotebookSessions()`. To terminate sessions, use `Runtime > Manage sessions` menu or the kernel API `terminateSession({sessionId})`.
