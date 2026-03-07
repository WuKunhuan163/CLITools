# GOOGLE.CDMCP -- Chrome DevTools MCP

Visual browser automation tool with session management, overlay indicators,
tab pinning, and privacy configuration. Provides agent-level control over
Chrome tabs via CDP.

## Prerequisites

- Chrome/Chromium running with `--remote-debugging-port=9222 --remote-allow-origins=*`
- Python `websocket-client` package

## Features

### Session System
```bash
CDMCP session create my_session     # Create a named session
CDMCP session list                  # List active sessions
CDMCP session close my_session      # Close a session
```

Each session owns a dedicated Chrome **window**. New tabs opened by the
session appear in that window. Only creating a new session or rebooting
a lost session opens a new window. Default timeout: 24 hours.

Sessions can be "checked out" -- the active session receives all new
operations until explicitly switched.

### Visual Overlays
1. **Badge** -- Blue "CDMCP" tag in top-right corner
2. **Focus border** -- Subtle blue border when agent is watching
3. **Lock overlay** -- Gray shade, flash on click, "Click to unlock" label
4. **Element highlight** -- Orange outline + label with element metadata
5. **Custom favicon** -- SVG icon on tab for visual identification
6. **Tab pinning** -- Native Chrome pin via extension `chrome.tabs` API (0.07s)

### MCP Interaction Interfaces
Generic interfaces that combine visual highlighting with CDP actions:

```python
from logic.cdmcp_loader import load_cdmcp_interact
interact = load_cdmcp_interact()

interact.mcp_click(session, "button.submit", label="Submit", dwell=1.0)
interact.mcp_type(session, "input#search", "query", char_delay=0.04)
interact.mcp_scroll(session, "down", 300)
interact.mcp_wait_and_click(session, ".result", timeout=10)
interact.mcp_navigate(session, "https://...", wait_selector="h1")
```

Each operation: highlight element -> hold for dwell time -> perform action -> remove highlight.

### Interactive Demo
```bash
CDMCP demo                 # Continuous: cycles through contacts/messages (default)
CDMCP demo --single        # Single-run: one interaction only
CDMCP demo --delay 0.5     # Faster interaction speed
```

The demo boots a local Chat app with a session ID in the title, then
demonstrates: selecting contacts, typing messages (with character-by-character
typing effect), clicking send, verifying delivery, draft messages (type
partially, switch contact, come back), and auto-relock after 10s if the
user unlocks.

A Turing machine (`DemoStateMachine`) tracks real-time demo state:
IDLE -> BOOTING -> SELECTING_CONTACT -> TYPING_MESSAGE -> SENDING ->
VERIFYING -> COUNTDOWN -> (repeat). State is persisted to
`data/state/demo.json`.

### Welcome Page

When a session boots, it shows a welcome/landing page (similar to Chrome's
new tab page) with session info, tool name, and connection status. The tool
then navigates to its target URL.

## CLI Usage

```bash
CDMCP status                                    # Chrome CDP + sessions + config
CDMCP navigate https://example.com              # Open tab with overlays
CDMCP focus example.com                         # Focus on tab
CDMCP lock example.com                          # Lock tab
CDMCP unlock example.com                        # Unlock tab
CDMCP highlight example.com "input[name=q]" --label "Search"
CDMCP cleanup example.com                       # Remove all overlays
CDMCP config                                    # Show config
CDMCP config --set allow_oauth_windows true     # Set config value
CDMCP tutorial                                  # Interactive setup guide
```

## Privacy Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `allow_oauth_windows` | `true` | Allow OAuth popups (Cursor IDE blocks these) |
| `log_interactions` | `true` | Log to `data/report/interaction_log.txt` |
| `session_default_timeout_sec` | `86400` | Session timeout (24h) |

## For Consumer Tools

Tools that depend on GOOGLE.CDMCP should:
1. Add `"GOOGLE.CDMCP"` to `dependencies` in `tool.json`
2. Use the loader:

```python
from logic.cdmcp_loader import (
    load_cdmcp_overlay, load_cdmcp_sessions, load_cdmcp_interact,
)
overlay = load_cdmcp_overlay()
sessions = load_cdmcp_sessions()
interact = load_cdmcp_interact()

session = sessions.create_session("my_tool")
session.boot("https://target-site.com")
cdp = session.get_cdp()
overlay.inject_badge(cdp, text="MyTool")
interact.mcp_click(cdp, "input[type=email]", label="Email", dwell=1.0)
interact.mcp_type(cdp, "input[type=email]", "user@example.com", char_delay=0.04)
```

## Testing

```bash
python3 tool/GOOGLE.CDMCP/test/test_00_help.py -v       # Help test
python3 tool/GOOGLE.CDMCP/test/test_01_overlay_visual.py -v   # 20 overlay tests
python3 tool/GOOGLE.CDMCP/test/test_02_full_workflow.py -v     # Lifecycle test
```
