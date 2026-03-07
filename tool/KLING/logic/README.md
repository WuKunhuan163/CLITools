# KLING Logic

Kling AI video generation via CDMCP. Uses the authenticated `klingai.com` session via Chrome DevTools Protocol.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — tab discovery, auth state, data extraction |
| `mcp/main.py` | MCP server configuration |

## API Functions (chrome/api.py)

| Function |
|----------|
| `find_kling_tab()` |
| `get_user_info()` |
| `get_points()` |
| `get_page_info()` |
| `get_generation_history()` |

Data source: localStorage (klingai_user) + DOM.
