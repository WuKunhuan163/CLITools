# SENTRY Logic

Sentry error monitoring via CDMCP. Uses the authenticated `sentry.io` session via Chrome DevTools Protocol.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — tab discovery, auth state, data extraction |
| `mcp/main.py` | MCP server configuration |

## API Functions (chrome/api.py)

| Function |
|----------|
| `find_sentry_tab()` |
| `get_auth_state()` |
| `get_page_info()` |
| `get_organizations()` |
| `get_projects()` |
| `get_issues()` |

Data source: same-origin REST API at /api/0/.
