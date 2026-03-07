# GOOGLE.CDMCP -- Chrome DevTools MCP

Visual browser automation tool with session management, overlay indicators,
tab pinning, and privacy configuration. Provides agent-level control over
Chrome tabs via CDP.

## Prerequisites

- Google Chrome (auto-launched if closed; download prompted if not installed)
- Python `websocket-client` package

## Features

### Session System
```bash
GOOGLE.CDMCP --mcp-session create my_session     # Create a named session
GOOGLE.CDMCP --mcp-session list                  # List active sessions
GOOGLE.CDMCP --mcp-session close my_session      # Close a session
GOOGLE.CDMCP --mcp-boot my_session               # Boot session (new window + welcome + demo)
```

Each session owns a dedicated Chrome **window**. New tabs opened by the
session appear in that window. Only creating a new session or rebooting
a lost session opens a new window.

Session timeouts:
- **Idle timeout** (default 1h): Auto-expires when no MCP operations occur
- **Forced timeout** (default None): Maximum session lifetime regardless of activity
- Any MCP operation resets the idle timer

Sessions can be "checked out" -- the active session receives all new
operations until explicitly switched.

Session concurrency limits:
```bash
GOOGLE.CDMCP --mcp-session-limit --max 3 --policy fail              # Refuse when limit reached
GOOGLE.CDMCP --mcp-session-limit --max 3 --policy kill_oldest_boot   # Evict oldest-created
GOOGLE.CDMCP --mcp-session-limit --max 3 --policy kill_oldest_activity # Evict least-recently-used
GOOGLE.CDMCP --mcp-session-limit                                      # Query current config
```

| Policy | Behavior |
|--------|----------|
| `fail` | Refuse creation, raise error listing active sessions |
| `kill_oldest_boot` | Evict the session with the earliest `created_at` |
| `kill_oldest_activity` | Evict the session with the oldest `last_activity` |

Config is persisted across process restarts.

### Chrome Lifecycle Management

`boot_tool_session()` automatically handles Chrome availability:
1. **Chrome running** -- Reuses existing CDP connection
2. **Chrome closed** -- Relaunches Chrome with CDP port (`--remote-debugging-port=9222`)
3. **Chrome not installed** -- Opens Chrome download page in system default browser

Profile directory: `~/ChromeDebugProfile` (persistent across sessions).

### Visual Overlays
1. **Badge** -- Blue "CDMCP [session_id]" tag in top-right corner
2. **Focus border** -- Subtle colored border when agent is watching
3. **Lock overlay** -- Gray shade with tool name (e.g., "Locked by Terminal Tool 'Figma'"), double-click to unlock
4. **Element highlight** -- Orange outline + label with element metadata
5. **Custom favicon** -- SVG icon on tab for visual identification
6. **Tab pinning** -- Native Chrome pin via CDP
7. **Timer/Counter** -- Bottom-left: last operation timestamp + persistent MPC count
8. **Cursor tracker** -- Bottom-right: real-time cursor position badge + blue dot overlay
9. **Tip banner** -- Top-center non-interactive notification (used for auth prompts)

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
interact.mcp_paste(session, "text to paste", selector="input#field")
interact.mcp_drag(session, x1, y1, x2, y2, steps=15, label="Draw")
```

Each operation: highlight element -> hold for dwell time -> perform action -> remove highlight.
All operations auto-lock the tab, increment the MPC counter, update cursor position, and reset the session idle timer. If the user unlocks mid-operation, the operation returns `{"ok": False, "interrupted": True}` and does not increment the counter.

### Unified Tool Boot (for tool developers)

Tools should use `boot_tool_session()` instead of implementing their own boot logic:

```python
from <cdmcp_session_manager> import boot_tool_session

result = boot_tool_session(
    "youtube",                # Session name
    timeout_sec=86400,        # Maximum lifetime (default 24h)
    idle_timeout_sec=3600,    # Idle timeout (default 1h)
)
session = result["session"]

# Open the app tab within the session window
tab_info = session.require_tab(
    "youtube", url_pattern="youtube.com",
    open_url="https://www.youtube.com",
)
cdp = CDPSession(tab_info["ws"])
```

`boot_tool_session` handles the full lifecycle:
1. Ensures Chrome is running (auto-launches if closed, prompts download if not installed)
2. Creates named session
3. Opens new Chrome window with welcome page
4. Pins the session tab
5. Applies CDMCP overlays (badge, focus, favicon)
6. Opens demo tab automatically
7. Starts persistent HTTP server for welcome/demo pages

### Tab Lifecycle Management

```python
tab_info = session.require_tab(
    label="my_tab",
    url_pattern="example.com",
    open_url="https://example.com",
    auto_open=True,
    wait_sec=10.0,
)
```

`require_tab()` handles:
- Finding existing tabs by label or URL pattern
- Opening missing tabs in the session window
- Full session reboot if the session window is lost (re-pins welcome tab, reopens demo, applies overlays)

### Interactive Demo
```bash
GOOGLE.CDMCP --mcp-demo                 # Continuous: cycles through contacts/messages
GOOGLE.CDMCP --mcp-demo --single        # Single-run: one interaction only
GOOGLE.CDMCP --mcp-demo --delay 0.5     # Faster interaction speed
```

The demo boots a local Chat app (served via `file://`), demonstrating:
selecting contacts, typing messages (character-by-character), clicking send,
verifying delivery, draft messages, and incoming message simulation.
Auto-relock after 10s if unlocked. Demo pauses immediately on unlock.

### Google Account Authentication

CDMCP provides integrated Google auth management:

```bash
GOOGLE.CDMCP --mcp-auth                   # Check Google login status
GOOGLE.CDMCP --mcp-login                  # Open login flow (dedicated tab with overlay tip)
GOOGLE.CDMCP --mcp-logout                 # Open logout flow
```

The welcome page shows an interactive ACCOUNT card that displays the signed-in user's email.
Auth state is checked via cookies (`SID`, `SSID`, `HSID`) and identity is probed from `myaccount.google.com`.
State is persisted in `google_identity.json` across processes. Other tools can verify auth via the interface:

```python
from <cdmcp_interface> import load_google_auth
auth = load_google_auth()
state = auth.get_cached_auth_state()  # {"signed_in": bool, "email": str, ...}
```

### Persistent HTTP Server

Session pages (welcome, demo, auth endpoint) are served by a background HTTP process
(`server_standalone.py`) that survives the parent Python process. The server writes its
PID and port to `server_state.json` and exposes `/health` for liveness checks.

### Welcome Page

Session boot shows a welcome page with session ID, timeout countdowns,
connection status, and Google Account card. Served via the persistent HTTP server.

## MCP Commands

All MCP commands use the `--mcp-` prefix.

```bash
GOOGLE.CDMCP --mcp-status                                    # Chrome CDP + sessions + config
GOOGLE.CDMCP --mcp-boot my_session                           # Boot session with welcome + demo
GOOGLE.CDMCP --mcp-navigate https://example.com              # Open tab with overlays
GOOGLE.CDMCP --mcp-focus example.com                         # Focus on tab
GOOGLE.CDMCP --mcp-lock example.com                          # Lock tab
GOOGLE.CDMCP --mcp-unlock example.com                        # Unlock tab
GOOGLE.CDMCP --mcp-highlight example.com "input[name=q]" --label "Search"
GOOGLE.CDMCP --mcp-cleanup example.com                       # Remove all overlays
GOOGLE.CDMCP --mcp-config                                    # Show config
GOOGLE.CDMCP --mcp-config --set allow_oauth_windows true     # Set config value
GOOGLE.CDMCP --mcp-session-limit --max 3 --policy fail       # Set max concurrent sessions
GOOGLE.CDMCP --mcp-tutorial                                  # Interactive setup guide
```

### Page Scanning
```bash
GOOGLE.CDMCP --mcp-scan youtube.com                          # Basic element scan
GOOGLE.CDMCP --mcp-scan youtube.com --full                   # Full scan (shadow + scroll + menus + APIs)
GOOGLE.CDMCP --mcp-scan youtube.com --shadow --apis          # Specific scan modes
GOOGLE.CDMCP --mcp-scan bilibili.com --full --screenshot /tmp/shot.png --output /tmp/elements.json
```

The `scan` command discovers all interactive elements on any page:
- **Elements**: Buttons, links, inputs, checkboxes, sliders, etc.
- **Shadow DOM** (`--shadow`): Web Components with shadow roots
- **Scrollable** (`--scroll`): Containers with overflow content
- **Menus** (`--menus`): Menu triggers and popups
- **APIs** (`--apis`): JavaScript API objects (YouTube, Colab, etc.)
- **`--full`**: All of the above

Output is saved as JSON for analysis and MCP development planning.

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
overlay.inject_lock(cdp, tool_name="MyTool")
interact.mcp_click(cdp, "input[type=email]", label="Email", dwell=1.0)
interact.mcp_type(cdp, "input[type=email]", "user@example.com", char_delay=0.04)
interact.mcp_paste(cdp, "bulk text", selector="textarea")
```

### Tab Window Targeting

`open_tab_in_session()` uses `chrome.tabs.create` API (via extension) for
reliable window targeting. The CDP `Target.createTarget(windowId)` parameter
is unreliable and may open tabs in the wrong window. Falls back to CDP with
post-creation verification and `chrome.tabs.move` correction.

### Session Cleanup

`close()` performs full cleanup:
1. Closes all registered tabs (demo, tool-specific)
2. Closes the lifetime (welcome) tab
3. Kills the demo subprocess

## Testing

```bash
TOOL --test GOOGLE.CDMCP        # Run all tests
# Individual tests:
test/test_00_help.py             # Help flag
test/test_01_overlay_visual.py   # Overlay rendering
test/test_02_full_workflow.py    # Lifecycle workflow
test/test_03_session_boot.py     # Session boot (pin + demo)
test/test_04_session_reboot.py   # Session reboot (window closure recovery)
```
