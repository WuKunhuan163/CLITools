# LUCIDCHART Logic

Lucidchart diagramming automation via CDMCP. Session-based tool with state machine tracking for `lucidchart.com`.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — session boot, document management, shape libraries, canvas editing, page management |
| `chrome/state_machine.py` | FSM tracking session lifecycle and recovery |

## Key API Functions (36 total)

Core: `boot_session()`, `get_session_status()`, `get_mcp_state()`, `get_auth_state()`, `get_page_info()`, `take_screenshot()`

Document management, shape libraries, canvas editing, page management.
