# ATLASSIAN Logic — Technical Reference

## Architecture

Standard CDMCP tool pattern:
- `chrome/api.py`: All CDP operations against `home.atlassian.com`
- `mcp/main.py`: MCPToolConfig for MCP server registration

## chrome/api.py

Tab discovery: `find_atlassian_tab()` searches for `home.atlassian.com` via `logic.chrome.session.find_tab()`.

Data source: gateway API at /gateway/api/.

Public API: `find_atlassian_tab()`, `get_me()`, `get_notifications()`, `get_user_preferences()`.

## mcp/main.py

Returns `MCPToolConfig` with tool name, MCP server ID, package type, capabilities, and required env vars.

## Gotchas

1. **Requires authenticated session**: The Chrome tab must be logged in. If not authenticated, API calls return auth-state errors.
2. **CDP port**: Defaults to `CDP_PORT` (9222). Ensure Chrome is running with `--remote-debugging-port=9222`.
