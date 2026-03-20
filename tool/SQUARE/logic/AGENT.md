# SQUARE Logic — Technical Reference

## Architecture

Standard CDMCP tool pattern:
- `chrome/api.py`: All CDP operations against `squareup.com`
- `mcp/main.py`: MCPToolConfig for MCP server registration

## chrome/api.py

Tab discovery: `find_square_tab()` searches for `squareup.com` via `logic.chrome.session.find_tab()`.

Data source: same-origin internal API.

Public API: `find_square_tab()`, `get_auth_state()`, `get_page_info()`, `get_dashboard_info()`.

## mcp/main.py

Returns `MCPToolConfig` with tool name, MCP server ID, package type, capabilities, and required env vars.

## Gotchas

1. **Requires authenticated session**: The Chrome tab must be logged in. If not authenticated, API calls return auth-state errors.
2. **CDP port**: Defaults to `CDP_PORT` (9222). Ensure Chrome is running with `--remote-debugging-port=9222`.
