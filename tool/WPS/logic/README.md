# WPS Logic

WPS Office / KDocs operations via CDMCP. Uses the authenticated `kdocs.cn` or `wps.com` session to access user info and recent documents.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — tab discovery, auth, user info, recent docs |
| `mcp/main.py` | MCP server configuration |

## API Functions (chrome/api.py)

| Function | Purpose |
|----------|---------|
| `find_wps_tab()` | Locate WPS/KDocs tab |
| `get_auth_state()` | Check login status |
| `get_page_info()` | Current page metadata |
| `get_user_info()` | Account details |
| `get_recent_docs()` | List recently accessed documents |
