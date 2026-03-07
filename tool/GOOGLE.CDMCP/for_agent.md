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
- `create_session(name, timeout_sec)` -- Create session in a dedicated Chrome window
- `session.boot(url)` -- Open lifetime tab at URL (new window only on first boot/reboot)
- `session.get_cdp()` -- Get live CDPSession (auto-reconnects, reopens tab if closed)
- `session.ensure_tab()` -- Reopen tab if closed (reopens in new window)
- `session.open_tab_in_session(url)` -- Open new tab in session's existing window
- `session.window_id` -- The Chrome window ID for this session
- `list_sessions()` / `close_session(name)`

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

## Workflow Pattern
1. `create_session("tool_name")` -> `session.boot(url)` (welcome page shown, then navigates)
2. `inject_badge(cdp)` + `inject_focus(cdp)` + `inject_favicon(cdp)`
3. `interact.mcp_click(cdp, selector, dwell=1.0)` for clicks with visual cue
4. `interact.mcp_type(cdp, selector, text, char_delay=0.04)` for typing with effect
5. `close_session(name)` when done

## Notes
- Requires Chrome CDP on port 9222
- All overlays are idempotent (re-injection replaces, not duplicates)
- Tab lifetime: auto-reopened if user closes it (in new window for session recovery)
- Tab pinning: native Chrome pin via extension chrome.tabs API
- Each session = one Chrome window; new tabs go into that window
- Demo runs continuously by default (Ctrl+C to stop)
- Demo auto-relocks 10s after user unlock, shows countdown between messages
