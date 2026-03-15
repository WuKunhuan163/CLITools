# LINEAR Logic

Linear product development via CDMCP. Uses the authenticated `linear.app` session via Chrome DevTools Protocol.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — tab discovery, auth state, data extraction |
| `mcp/main.py` | MCP server configuration |

## API Functions (chrome/api.py)

| Function |
|----------|
| `find_linear_tab()` |
| `get_auth_state()` |
| `get_user_info()` |
| `get_page_info()` |

Data source: localStorage (ApplicationStore).
