# ASANA Logic — Technical Reference

## Architecture

Standard CDMCP tool pattern:
- `chrome/api.py`: All CDP operations against `app.asana.com`
- `mcp/main.py`: MCPToolConfig for MCP server registration

## chrome/api.py

Tab discovery: `find_asana_tab()` searches for `app.asana.com` via `logic.chrome.session.find_tab()`.

Data source: same-origin REST API at /api/1.0/.

Public API: `find_asana_tab()`, `get_me()`, `list_workspaces()`, `list_projects()`, `list_tasks()`, `get_task()`, `create_task()`, `create_project()`, `complete_task()`, `search_tasks()`.

## mcp/main.py

Returns `MCPToolConfig` with tool name, MCP server ID, package type, capabilities, and required env vars.

## Gotchas

1. **Requires authenticated session**: The Chrome tab must be logged in. If not authenticated, API calls return auth-state errors.
2. **CDP port**: Defaults to `CDP_PORT` (9222). Ensure Chrome is running with `--remote-debugging-port=9222`.
