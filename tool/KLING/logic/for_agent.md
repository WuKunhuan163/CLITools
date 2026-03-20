# KLING Logic — Technical Reference

## Architecture

Standard CDMCP tool pattern:
- `chrome/api.py`: All CDP operations against `klingai.com`
- `mcp/main.py`: MCPToolConfig for MCP server registration

## chrome/api.py

Tab discovery: `find_kling_tab()` searches for `klingai.com` via `logic.chrome.session.find_tab()`.

Data source: localStorage (klingai_user) + DOM.

Public API: `find_kling_tab()`, `get_user_info()`, `get_points()`, `get_page_info()`, `get_generation_history()`.

## mcp/main.py

Returns `MCPToolConfig` with tool name, MCP server ID, package type, capabilities, and required env vars.

## Gotchas

1. **Requires authenticated session**: The Chrome tab must be logged in. If not authenticated, API calls return auth-state errors.
2. **CDP port**: Defaults to `CDP_PORT` (9222). Ensure Chrome is running with `--remote-debugging-port=9222`.
