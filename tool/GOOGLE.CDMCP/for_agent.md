# GOOGLE.CDMCP -- Agent Reference

## Quick Start
```
CDMCP --mcp-status                              # Check availability + sessions
CDMCP --mcp-demo                                # Continuous interaction demo (default)
CDMCP --mcp-demo --single                       # Single-run demo
CDMCP --mcp-boot my_session                     # Boot session (new window + welcome + demo)
CDMCP --mcp-auth                                # Google login status
CDMCP --mcp-login                               # Initiate Google login flow
CDMCP --mcp-logout                              # Initiate Google logout flow
CDMCP --mcp-navigate URL                        # Open URL in new tab
CDMCP --mcp-navigate URL --tab-id ID            # Navigate existing tab to URL
CDMCP --mcp-activate TAB_ID                     # Switch focus to a tab
CDMCP --mcp-minimize                            # Minimize session window
CDMCP --mcp-restore                             # Restore session window
CDMCP --mcp-ensure-window                       # Verify window alive; reboot if needed
CDMCP --mcp-screenshot                          # Screenshot last session tab
CDMCP --mcp-screenshot --tab-id ID --output P   # Screenshot specific tab to path
CDMCP --mcp-focus-element PATTERN SELECTOR      # Focus a DOM element in a tab
CDMCP --mcp-click PATTERN [SELECTOR]            # Click element (or focused element)
CDMCP --mcp-scroll PATTERN --dx N --dy N        # Scroll in a tab
CDMCP --mcp-auth                                # Check Google login state
CDMCP --mcp-login                               # Login (sync, waits + auto-closes tab)
CDMCP --mcp-logout                              # Logout (clicks Continue, auto-closes)
CDMCP --mcp-save-auth                           # Save auth cookies for auto-login
CDMCP --mcp-restore-auth                        # Restore saved cookies (no user interaction)
CDMCP --mcp-session list                        # List all sessions
CDMCP --mcp-state                               # Print comprehensive MCP state
```

## Session API

**Unified Boot (preferred for all tools):**
```python
from <cdmcp_session_manager> import boot_tool_session
result = boot_tool_session("tool_name", timeout_sec=86400, idle_timeout_sec=3600)
session = result["session"]  # CDMCPSession with pinned tab + demo tab
```

`boot_tool_session` handles: ensure Chrome -> welcome page -> new window -> pin -> overlays -> demo tab -> persistent HTTP server.

If Chrome is closed, `boot_tool_session` auto-relaunches it. If Chrome is not installed, it opens the download page in the system default browser.

**Session Methods:**
- `session.require_tab(label, url_pattern, open_url)` -- Find/open app tab in session window
- `session.get_cdp()` -- Get live CDPSession (auto-reconnects)
- `session.open_tab_in_session(url)` -- Open new tab in session's window (refreshes idle timeout)
- `session.touch()` -- Refresh idle timeout
- `session.window_id` -- Chrome window ID
- `list_sessions()` / `close_session(name)`

**Chrome Lifecycle:**
```python
from <cdmcp_session_manager> import ensure_chrome
result = ensure_chrome()  # {"ok": True, "action": "already_running"|"relaunched"|"chrome_not_installed"}
```

**CRITICAL: Tools must NOT implement their own boot logic.** Use `boot_tool_session` then `session.require_tab` to open the app tab.

## MCP Interaction Interfaces
```python
from logic.cdmcp_loader import load_cdmcp_interact
interact = load_cdmcp_interact()

interact.mcp_click(cdp, "a.link", label="Open link", dwell=1.0)
interact.mcp_type(cdp, "input#search", "query text", char_delay=0.04)
interact.mcp_wait_and_click(cdp, ".result", timeout=10, dwell=1.0)
interact.mcp_navigate(cdp, "https://url", wait_selector="h1")
interact.mcp_scroll(cdp, "down", 300)
interact.mcp_paste(cdp, "text", selector="textarea")
interact.mcp_drag(cdp, x1, y1, x2, y2, steps=15, label="Draw", tool_name="Figma")
```

All operations: auto-lock -> highlight/cursor -> action -> count MPC -> reset idle timer.
If user unlocks mid-operation: returns `{"ok": False, "interrupted": True}`, counter not incremented.

## Overlay API (via `logic.cdmcp_loader`)
```python
from logic.cdmcp_loader import load_cdmcp_overlay
ov = load_cdmcp_overlay()
ov.inject_badge(cdp, text="CDMCP", color="#1a73e8")
ov.inject_focus(cdp, color="#1a73e8")
ov.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25, tool_name="MyTool")
ov.inject_highlight(cdp, selector, label, color="#e8710a")
ov.inject_tip(cdp, text="Please sign in", bg_color="#1a73e8")
ov.inject_favicon(cdp, svg_color="#1a73e8", letter="C")
ov.update_cursor_position(cdp, x, y)   # Update cursor tracker
ov.pin_tab_by_target_id(target_id)
ov.set_lock_passthrough(cdp, True)  # Allow CDP clicks through lock
ov.remove_all_overlays(cdp)
```

Lock overlay features:
- Bottom-left: "Last: HH:MM:SS, MPC: N" (persistent counter, survives page navigation)
- Bottom-right: "Cursor: X, Y" + blue tracking dot
- Double-click label to unlock; all other mouse events blocked
- Flash effect on click attempts

## Google Auth API
```python
from <cdmcp_interface> import load_google_auth
auth = load_google_auth()
state = auth.get_cached_auth_state()           # {"signed_in": bool, "email": str, ...}
auth.initiate_login(session)                    # Open login tab + track
auth.initiate_logout(session)                   # Open logout tab + track
```

## Workflow Pattern (for tool developers)
1. `boot_tool_session("tool_name")` -- Ensures Chrome + creates session + pinned tab + demo
2. `session.require_tab("app", url_pattern="app.com", open_url="https://app.com")` -- Opens app tab
3. `overlay.inject_badge(cdp)` + `inject_focus(cdp)` + `inject_favicon(cdp)` -- Customize app tab
4. `interact.mcp_click(cdp, selector, dwell=1.0)` -- Clicks with visual cue + cursor tracking
5. `interact.mcp_drag(cdp, x1, y1, x2, y2)` -- Canvas drag with cursor dot
6. `interact.mcp_type(cdp, selector, text)` -- Typing with effect
7. `close_session(name)` -- Cleanup

## `@requires_cdp` — Unified Prerequisite Gate

Every Chrome-dependent API function is decorated with `@requires_cdp()`, which runs a 3-stage check **before** the function body executes:

| Stage | Check | Recovery |
|-------|-------|----------|
| 1. Chrome installed | `is_chrome_cdp_available()` | Calls `ensure_chrome()` to auto-relaunch |
| 2. CDP debug mode | HTTP probe on port 9222 | Waits 2s after relaunch, retries |
| 3. Session window | `ensure_session_window()` | Full session reboot if window lost |

```python
@requires_cdp()                       # Full 3-stage (Chrome + CDP + session)
def navigate(url, port=CDP_PORT): ...

@requires_cdp(check_session=False)    # Stages 1+2 only (Chrome + CDP)
def google_auth_status(port=CDP_PORT): ...
```

**Tool developers never need to call `ensure_session_window()` or `is_chrome_cdp_available()` manually.** The decorator extracts the `port` parameter from the wrapped function's signature automatically.

If any stage fails, the function returns early with `{"ok": False, "step": "...", "error": "..."}` without executing the body.

**Decorated functions (15 total):**
- Full check (`@requires_cdp()`): `navigate`, `focus_tab`, `lock_tab`, `unlock_tab`, `highlight_element`, `clear_highlight`, `cleanup_tab`, `navigate_tab`, `activate_tab`, `minimize_window`, `restore_window`, `run_demo`
- CDP only (`@requires_cdp(check_session=False)`): `google_auth_status`, `google_auth_login`, `google_auth_logout`

**Not decorated** (local state only): `status`, `list_sessions`, `create_session`, `close_session`, `get_config`, `set_config_value`, `boot_session` (has own lifecycle).

## Lessons Learned
- **All Chrome operations inherit prerequisites via `@requires_cdp`.** No manual prerequisite calls needed.
- **Never navigate the session tab** to the app URL. Always use `require_tab` for separate app tabs.
- **Demo tab must auto-start** on every boot/reboot. The unified `boot_tool_session` handles this.
- **Window closure triggers full_reboot**: `require_tab` detects window loss and calls `full_reboot()`.
- **Each tool reuses CDMCP interfaces**: No duplicate boot/overlay/session logic in tool code.
- **idle_timeout_sec** resets on any `session.touch()` call (done automatically by MPC operations and tab opens).
- **MPC counter is persistent**: Stored in `state.json`, restored into JS overlay on lock re-injection after page navigation.
- **CDP `Target.createTarget(windowId)` is unreliable**: Use `chrome.tabs.create({windowId})` via extension API.
- **Chrome may be closed unexpectedly**: `ensure_chrome()` handles auto-relaunch transparently.
- **Tab isolation**: `require_tab()` only claims tabs within the session's CDMCP browser window, not from the user's regular tabs.
- **Persistent HTTP server**: Welcome/demo pages survive process exit via `server_standalone.py`.
- **Interrupt handling**: All MPC operations check `_was_unlocked()` and return failure if user unlocked mid-operation.
