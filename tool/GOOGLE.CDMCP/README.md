# GOOGLE.CDMCP — Chrome DevTools MCP

Visual browser automation tool with session management, overlay indicators, tab pinning, and privacy configuration. Provides agent-level control over Chrome tabs via CDP.

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

Sessions have lifetime tabs that auto-reopen if closed. Default timeout: 24 hours.

### Visual Overlays
1. **Badge** — Blue "CDMCP" tag in top-right corner
2. **Focus border** — Subtle blue border when agent is watching
3. **Lock overlay** — Gray shade, flash on click, "Click to unlock" label
4. **Element highlight** — Orange outline + label with element metadata
5. **Custom favicon** — SVG icon on tab for visual identification
6. **Tab pinning** — `activate_tab` brings the tab to foreground

### Interactive Demo
```bash
CDMCP demo                 # Single-run: 8-step interaction sequence
CDMCP demo --loop           # Continuous: cycles through contacts/messages
CDMCP demo --delay 0.5      # Faster interaction speed
```

The demo boots a local Chat app, then demonstrates selecting contacts, typing messages, clicking send, and verifying delivery — all with overlay effects.

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
from logic.cdmcp_loader import load_cdmcp_overlay, load_cdmcp_sessions
overlay = load_cdmcp_overlay()
sessions = load_cdmcp_sessions()

session = sessions.create_session("my_tool")
session.boot("https://target-site.com")
cdp = session.get_cdp()
overlay.inject_badge(cdp, text="MyTool")
overlay.inject_highlight(cdp, "input[type=email]", label="Email field")
```

## Testing

```bash
python3 tool/GOOGLE.CDMCP/test/test_00_help.py -v       # Help test
python3 tool/GOOGLE.CDMCP/test/test_01_overlay_visual.py -v   # 20 overlay tests
python3 tool/GOOGLE.CDMCP/test/test_02_full_workflow.py -v     # Lifecycle test
```
