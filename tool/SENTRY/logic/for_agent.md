# SENTRY Logic — Technical Reference

## Architecture

Standard CDMCP tool pattern:
- `chrome/api.py`: All CDP operations against `sentry.io`
- `mcp/main.py`: MCPToolConfig for MCP server registration

## chrome/api.py

Tab discovery: `find_sentry_tab()` searches for `sentry.io` via `logic.chrome.session.find_tab()`.

Data source: same-origin REST API at /api/0/.

Public API: `find_sentry_tab()`, `get_auth_state()`, `get_page_info()`, `get_organizations()`, `get_projects()`, `get_issues()`.

## mcp/main.py

Returns `MCPToolConfig` with tool name, MCP server ID, package type, capabilities, and required env vars.

## Gotchas

1. **Requires authenticated session**: The Chrome tab must be logged in. If not authenticated, API calls return auth-state errors.
2. **CDP port**: Defaults to `CDP_PORT` (9222). Ensure Chrome is running with `--remote-debugging-port=9222`.
