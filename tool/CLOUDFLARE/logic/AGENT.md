# CLOUDFLARE Logic — Technical Reference

## Architecture

Standard CDMCP tool pattern:
- `chrome/api.py`: All CDP operations against `dash.cloudflare.com`
- `mcp/main.py`: MCPToolConfig for MCP server registration

## chrome/api.py

Tab discovery: `find_cloudflare_tab()` searches for `dash.cloudflare.com` via `logic.chrome.session.find_tab()`.

Data source: same-origin proxy at /api/v4/.

Public API: `find_cloudflare_tab()`, `get_user()`, `get_account()`, `list_zones()`, `get_zone()`, `list_dns_records()`, `list_workers()`, `list_pages_projects()`, `list_kv_namespaces()`.

## mcp/main.py

Returns `MCPToolConfig` with tool name, MCP server ID, package type, capabilities, and required env vars.

## Gotchas

1. **Requires authenticated session**: The Chrome tab must be logged in. If not authenticated, API calls return auth-state errors.
2. **CDP port**: Defaults to `CDP_PORT` (9222). Ensure Chrome is running with `--remote-debugging-port=9222`.
