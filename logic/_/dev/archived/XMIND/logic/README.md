# XMIND Logic

XMind mind mapping via CDMCP. Uses CDMCP sessions to manage the `app.xmind.com` browser tab with visual overlays, state machine tracking, and MCP interaction interfaces.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — session boot, map CRUD, node operations, export |
| `chrome/state_machine.py` | `XMState` FSM — tracks session lifecycle (boot, idle, navigate, edit) |
| `mcp/main.py` | MCP server configuration |

## Key Difference from Standard CDMCP Tools

XMIND uses the full CDMCP session manager (not just `find_tab`). It boots a named session with overlays, maintains state across operations, and supports rich interactions (add/edit/delete nodes, undo/redo, zoom, export).
