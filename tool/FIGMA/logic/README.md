# FIGMA Logic

Figma design tool automation via CDMCP. Session-based tool with state machine tracking for `figma.com`.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — session boot, file management, canvas editing, shape/text tools, layers, components, export |
| `chrome/state_machine.py` | FSM tracking session lifecycle and recovery |

## Key API Functions (50 total)

Core: `boot_session()`, `get_session_status()`, `get_mcp_state()`, `get_auth_state()`, `get_page_info()`, `take_screenshot()`

File management, canvas editing, shape/text tools, layers, components, export.
