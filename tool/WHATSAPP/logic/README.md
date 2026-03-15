# WHATSAPP Logic

WhatsApp Web messaging via CDMCP. Uses the authenticated `web.whatsapp.com` session via Chrome DevTools Protocol.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — tab discovery, auth state, data extraction |
| `mcp/main.py` | MCP server configuration |

## API Functions (chrome/api.py)

| Function |
|----------|
| `find_whatsapp_tab()` |
| `get_auth_state()` |
| `get_page_info()` |
| `get_chats()` |
| `get_profile()` |
| `search_contact()` |
| `send_message()` |

Data source: DOM scraping + URL scheme messaging.
