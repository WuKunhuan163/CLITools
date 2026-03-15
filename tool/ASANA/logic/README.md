# ASANA Logic

Asana project management via CDMCP. Uses the authenticated `app.asana.com` session via Chrome DevTools Protocol.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — tab discovery, auth state, data extraction |
| `mcp/main.py` | MCP server configuration |

## API Functions (chrome/api.py)

| Function |
|----------|
| `find_asana_tab()` |
| `get_me()` |
| `list_workspaces()` |
| `list_projects()` |
| `list_tasks()` |
| `get_task()` |
| `create_task()` |
| `create_project()` |
| `complete_task()` |
| `search_tasks()` |

Data source: same-origin REST API at /api/1.0/.
