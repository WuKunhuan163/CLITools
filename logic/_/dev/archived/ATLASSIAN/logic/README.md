# ATLASSIAN Logic

Atlassian account management via CDMCP. Uses the authenticated `home.atlassian.com` session via Chrome DevTools Protocol.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — tab discovery, auth state, data extraction |
| `mcp/main.py` | MCP server configuration |

## API Functions (chrome/api.py)

| Function |
|----------|
| `find_atlassian_tab()` |
| `get_me()` |
| `get_notifications()` |
| `get_user_preferences()` |

Data source: gateway API at /gateway/api/.
