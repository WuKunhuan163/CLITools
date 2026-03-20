# SQUARE Logic

Square business platform via CDMCP. Uses the authenticated `squareup.com` session via Chrome DevTools Protocol.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — tab discovery, auth state, data extraction |
| `mcp/main.py` | MCP server configuration |

## API Functions (chrome/api.py)

| Function |
|----------|
| `find_square_tab()` |
| `get_auth_state()` |
| `get_page_info()` |
| `get_dashboard_info()` |

Data source: same-origin internal API.
