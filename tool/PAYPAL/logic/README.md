# PAYPAL Logic

PayPal payment management via CDMCP. Uses the authenticated `paypal.com` session via Chrome DevTools Protocol.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — tab discovery, auth state, data extraction |
| `mcp/main.py` | MCP server configuration |

## API Functions (chrome/api.py)

| Function |
|----------|
| `find_paypal_tab()` |
| `get_auth_state()` |
| `get_page_info()` |
| `get_account_info()` |
| `get_recent_activity()` |

Data source: authenticated session + DOM.
