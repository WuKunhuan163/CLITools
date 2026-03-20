# INTERCOM Logic

Intercom customer messaging via CDMCP. Uses the authenticated `app.intercom.com` session via Chrome DevTools Protocol.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — tab discovery, auth state, data extraction |
| `mcp/main.py` | MCP server configuration |

## API Functions (chrome/api.py)

| Function |
|----------|
| `find_intercom_tab()` |
| `get_auth_state()` |
| `get_page_info()` |
| `get_conversations()` |
| `get_contacts()` |

Data source: internal API + DOM scraping fallback.
