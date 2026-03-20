# WHATSAPP Logic — Technical Reference

## Architecture

Standard CDMCP tool pattern:
- `chrome/api.py`: All CDP operations against `web.whatsapp.com`
- `mcp/main.py`: MCPToolConfig for MCP server registration

## chrome/api.py

Tab discovery: `find_whatsapp_tab()` searches for `web.whatsapp.com` via `logic.chrome.session.find_tab()`.

Data source: DOM scraping + URL scheme messaging.

Public API: `find_whatsapp_tab()`, `get_auth_state()`, `get_page_info()`, `get_chats()`, `get_profile()`, `search_contact()`, `send_message()`.

## mcp/main.py

Returns `MCPToolConfig` with tool name, MCP server ID, package type, capabilities, and required env vars.

## Bulk Messaging Safety

WhatsApp aggressively rate-limits automated messaging:
- **New numbers**: Max ~200 messages/day before risk of ban
- **Established accounts**: Higher limit but still enforce delays
- **Recommended delay**: 3-5 seconds between messages (use `random.uniform(2, 5)`)
- **Always check**: `get_auth_state()` before starting bulk operations
- **Stop on errors**: If `send_message()` fails 3 times consecutively, stop and report

For bulk messaging workflow, see the `recipes` skill: `SKILLS show recipes`.

## Session Recovery

If the WhatsApp tab becomes unresponsive:
1. Call `find_whatsapp_tab()` — if None, the tab was closed
2. User must re-open `web.whatsapp.com` in Chrome and re-scan the QR code
3. Wait for page load (check `get_auth_state()` returns `authenticated: true`)
4. Resume operations

## Gotchas

1. **Requires authenticated session**: The Chrome tab must be logged in. If not authenticated, API calls return auth-state errors.
2. **CDP port**: Defaults to `CDP_PORT` (9222). Ensure Chrome is running with `--remote-debugging-port=9222`.
3. **URL scheme messaging**: `send_message()` uses WhatsApp's `wa.me` URL scheme to open chats, which may trigger navigation. Wait for page stabilization after each send.
4. **Contact names with special characters**: Contact names containing emojis or RTL text may need sanitization for search operations.
