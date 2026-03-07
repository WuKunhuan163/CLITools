# GOOGLE.CDMCP -- Agent Reference

## Quick Start
```
CDMCP status                                    # Check availability + sessions
CDMCP demo                                      # Continuous interaction demo (default)
CDMCP demo --single                             # Single-run demo
CDMCP session create my_session                 # Create named session
CDMCP navigate https://example.com              # Open tab with overlays
CDMCP lock example.com                          # Lock tab
CDMCP highlight example.com "input[type=email]" --label "Email"
CDMCP cleanup example.com                       # Remove all overlays
```

## Session API

**Unified Boot (preferred for all tools):**
```python
from <cdmcp_session_manager> import boot_tool_session
result = boot_tool_session("tool_name", timeout_sec=86400, idle_timeout_sec=3600)
session = result["session"]  # CDMCPSession with pinned tab + demo tab
```

`boot_tool_session` handles: welcome page -> new window -> pin -> overlays -> demo tab -> demo process.

**Session Methods:**
- `session.require_tab(label, url_pattern, open_url)` -- Find/open app tab in session window
- `session.get_cdp()` -- Get live CDPSession (auto-reconnects)
- `session.open_tab_in_session(url)` -- Open new tab in session's window
- `session.window_id` -- Chrome window ID
- `list_sessions()` / `close_session(name)`

**CRITICAL: Tools must NOT implement their own boot logic.** Use `boot_tool_session` then `session.require_tab` to open the app tab.

## MCP Interaction Interfaces
```python
from logic.cdmcp_loader import load_cdmcp_interact
interact = load_cdmcp_interact()

# Highlight + dwell + click (1s focus on element before clicking)
interact.mcp_click(cdp, "a.link", label="Open link", dwell=1.0)

# Highlight + type character by character (typing effect)
interact.mcp_type(cdp, "input#search", "query text", char_delay=0.04)

# Wait for element to appear, then click with dwell
interact.mcp_wait_and_click(cdp, ".result", timeout=10, dwell=1.0)

# Navigate and wait for selector
interact.mcp_navigate(cdp, "https://url", wait_selector="h1")

# Scroll with visual indicator
interact.mcp_scroll(cdp, "down", 300)
```

## Overlay API (via `logic.cdmcp_loader`)
```python
from logic.cdmcp_loader import load_cdmcp_overlay
ov = load_cdmcp_overlay()
ov.inject_badge(cdp, text="CDMCP", color="#1a73e8")
ov.inject_focus(cdp, color="#1a73e8")
ov.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25)
ov.inject_highlight(cdp, selector, label, color="#e8710a")
  # Returns: {ok, selector, element: {tag, type, name, ...}, rect}
ov.inject_favicon(cdp, svg_color="#1a73e8", letter="C")
ov.activate_tab(tab_id, port)
ov.pin_tab_by_target_id(target_id)  # Native Chrome pin (0.07s)
ov.set_lock_passthrough(cdp, True)  # Allow CDP clicks through lock
ov.remove_all_overlays(cdp)
```

## Demo State Machine
```python
from logic.cdmcp_loader import load_cdmcp_demo_state
ds = load_cdmcp_demo_state()
machine = ds.get_demo_machine()
print(machine.to_dict())  # Real-time state: selecting_contact, typing, etc.
```
State file: `data/state/demo.json`

## Config
```
CDMCP config                                     # Show all
CDMCP config --set allow_oauth_windows true      # Set value
CDMCP config --reset                              # Reset defaults
```

## Workflow Pattern (for tool developers)
1. `boot_tool_session("tool_name")` -- Creates session with pinned tab + demo
2. `session.require_tab("app", url_pattern="app.com", open_url="https://app.com")` -- Opens app tab
3. `overlay.inject_badge(cdp)` + `inject_focus(cdp)` + `inject_favicon(cdp)` -- Customize app tab
4. `interact.mcp_click(cdp, selector, dwell=1.0)` -- Clicks with visual cue
5. `interact.mcp_type(cdp, selector, text)` -- Typing with effect
6. `close_session(name)` -- Cleanup

## Page Scanning
```
CDMCP scan --pattern "youtube.com" --full --output /tmp/scan.json --screenshot /tmp/scan.png
```
Flags: `--shadow`, `--scroll`, `--menus`, `--apis`, `--full` (all).

## Tab Window Targeting
```python
ov.create_tab_in_window(url, window_id, port)   # Reliable: uses chrome.tabs.create API
ov.move_tab_to_window(cdp_target_id, window_id)  # Move existing tab to correct window
```
`open_tab_in_session()` uses `chrome.tabs.create` (primary) with CDP fallback + verification + move.

## Lessons Learned
- **Never navigate the session tab** to the app URL. Always use `require_tab` for separate app tabs.
- **Demo tab must auto-start** on every boot/reboot. The unified `boot_tool_session` handles this.
- **Window closure triggers full_reboot**: `require_tab` detects window loss and calls `full_reboot()`.
- **Each tool reuses CDMCP interfaces**: No duplicate boot/overlay/session logic in tool code.
- **idle_timeout_sec** resets on any `session.touch()` call (done automatically by operations).
- **CDP `Target.createTarget(windowId)` is unreliable**: Sometimes opens tabs in the wrong window. Always use `chrome.tabs.create({windowId})` via extension API for reliable window targeting.
- **Session `close()` must clean up everything**: Close all registered tabs (not just lifetime tab) and kill demo subprocess. Orphaned tabs and processes cause confusion.
- **Test with repeated iterations**: Intermittent bugs (e.g., tab opening in wrong window at ~25% rate) only surface with repeated testing (8+ iterations).
- **Verify tab window after creation**: After creating a tab via any method, verify its `Browser.getWindowForTarget` and use `chrome.tabs.move` if it's in the wrong window.

## Notes
- Requires Chrome CDP on port 9222
- All overlays are idempotent (re-injection replaces, not duplicates)
- Tab lifetime: auto-reopened if user closes it (in new window for session recovery)
- Tab pinning: native Chrome pin via extension chrome.tabs API
- Each session = one Chrome window; new tabs go into that window
- Demo runs continuously by default; auto-relocks 10s after user unlock
- Session close: cleans up all tabs + kills demo subprocess
