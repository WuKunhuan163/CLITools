# GMAIL Logic

Gmail email client via CDMCP. Uses the authenticated `mail.google.com` session to read inbox, search, and send emails via DOM manipulation.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — inbox reading, search, compose, send |
| `mcp/main.py` | MCP server configuration |

## API Functions (chrome/api.py)

| Function | Purpose |
|----------|---------|
| `find_gmail_tab()` | Locate Gmail tab |
| `get_auth_state()` | Check login status |
| `get_page_info()` | Page title, unread count |
| `get_inbox()` | Read inbox email rows |
| `get_labels()` | List Gmail labels |
| `search_emails()` | Search via Gmail search bar |
| `send_email()` | Compose and send via UI |
