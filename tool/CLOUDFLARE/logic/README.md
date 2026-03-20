# CLOUDFLARE Logic

Cloudflare account management via CDMCP. Uses the authenticated `dash.cloudflare.com` session via Chrome DevTools Protocol.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — tab discovery, auth state, data extraction |
| `mcp/main.py` | MCP server configuration |

## API Functions (chrome/api.py)

| Function |
|----------|
| `find_cloudflare_tab()` |
| `get_user()` |
| `get_account()` |
| `list_zones()` |
| `get_zone()` |
| `list_dns_records()` |
| `list_workers()` |
| `list_pages_projects()` |
| `list_kv_namespaces()` |

Data source: same-origin proxy at /api/v4/.
