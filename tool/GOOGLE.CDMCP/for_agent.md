# GOOGLE.CDMCP — Agent Reference

## Quick Start
```
CDMCP status                                    # Check availability + sessions
CDMCP demo                                      # Single-run interaction demo
CDMCP demo --loop                               # Continuous demo (Ctrl+C to stop)
CDMCP session create my_session                 # Create named session
CDMCP navigate https://example.com              # Open tab with overlays
CDMCP lock example.com                          # Lock tab
CDMCP highlight example.com "input[type=email]" --label "Email"
CDMCP cleanup example.com                       # Remove all overlays
```

## Session API
- `create_session(name, timeout_sec)` — Create session, default timeout 24h
- `session.boot(url)` — Open lifetime tab at URL
- `session.get_cdp()` — Get live CDPSession (auto-reconnects)
- `session.ensure_tab()` — Reopen tab if closed
- `list_sessions()` / `close_session(name)`

## Overlay API (via `logic.cdmcp_loader`)
```python
from logic.cdmcp_loader import load_cdmcp_overlay
ov = load_cdmcp_overlay()
ov.inject_badge(cdp, text="CDMCP", color="#1a73e8")
ov.inject_focus(cdp, color="#1a73e8")
ov.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25)
ov.inject_highlight(cdp, selector, label, color="#e8710a")
  # Returns: {ok, selector, element: {tag, type, name, placeholder, ariaLabel, text}, rect}
ov.inject_favicon(cdp, svg_color="#1a73e8", letter="C")
ov.activate_tab(tab_id, port)
ov.remove_all_overlays(cdp)
```

## Config
```
CDMCP config                                     # Show all
CDMCP config --set allow_oauth_windows true      # Set value
CDMCP config --reset                              # Reset defaults
```
- `allow_oauth_windows: true` — OAuth allowed (unlike Cursor IDE browser)
- `session_default_timeout_sec: 86400` — 24h default

## Workflow Pattern
1. `create_session("tool_name")` -> `session.boot(url)`
2. `inject_badge(cdp)` + `inject_focus(cdp)` + `inject_favicon(cdp)`
3. `inject_lock(cdp)` -> perform CDP operations -> `remove_lock(cdp)`
4. `inject_highlight(cdp, selector, label)` -> interact -> `remove_highlight(cdp)`
5. `cleanup_tab(pattern)` or `close_session(name)` when done

## Notes
- Requires Chrome CDP on port 9222
- All overlays are idempotent (re-injection replaces, not duplicates)
- Tab lifetime: auto-reopened if user closes it
- Tab pinning: `activate_tab` brings tab to foreground
- Custom favicon: SVG-based, shows in Chrome tab bar
