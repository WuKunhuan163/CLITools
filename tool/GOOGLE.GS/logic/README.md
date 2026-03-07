# GOOGLE.GS Logic

Google Scholar research via CDMCP. Session-based tool with state machine tracking for `scholar.google.com`.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — session boot, paper search, filtering, citations, pdf links, author profiles, library |
| `chrome/state_machine.py` | FSM tracking session lifecycle and recovery |

## Key API Functions (17 total)

Core: `boot_session()`, `get_session_status()`, `get_mcp_state()`, `get_auth_state()`, `get_page_info()`, `take_screenshot()`

Paper search, filtering, citations, PDF links, author profiles, library.
