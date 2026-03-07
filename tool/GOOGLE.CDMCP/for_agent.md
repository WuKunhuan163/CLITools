# GOOGLE.CDMCP — Agent Reference

## Quick Start
```
CDMCP status                                    # Check Chrome availability
CDMCP navigate https://example.com              # Open tab with overlays
CDMCP focus example.com                         # Focus on tab
CDMCP lock example.com                          # Lock tab (prevent user interaction)
CDMCP unlock example.com                        # Unlock tab
CDMCP highlight example.com "input[type=email]" --label "Email field"
CDMCP cleanup example.com                       # Remove all overlays
```

## Overlay API (`logic.cdp.overlay`)
- `inject_badge(session, text, color)` — Top-right "CDMCP" tag
- `inject_focus(session, color)` — Blue border glow
- `inject_lock(session, base_opacity, flash_opacity)` — Gray lock shade with unlock label
- `inject_highlight(session, selector, label, color)` — Element outline with label; returns `{ok, selector, element: {tag, type, name, placeholder, ariaLabel, text}, rect: {top, left, width, height}}`
- `remove_all_overlays(session)` — Clean all overlays from tab
- `get_session(tab_info)` / `get_session_for_url(pattern)` — Get CDPSession

## Privacy Config (`CDMCP config`)
- `allow_oauth_windows: true` — OAuth popups allowed (unlike Cursor IDE browser)
- `log_interactions: true` — Logs to `data/report/interaction_log.txt`
- Full config: `CDMCP config`

## Workflow Pattern
1. `CDMCP navigate <url>` — Opens tab with badge + focus
2. `CDMCP lock <pattern>` — Lock before automated interactions
3. `CDMCP highlight <pattern> <selector>` — Show target element
4. Perform CDP operations (click, type, etc.) via `logic.chrome.session`
5. `CDMCP cleanup <pattern>` — Remove overlays when done

## Notes
- Requires Chrome CDP on port 9222
- All overlays are idempotent (re-injection replaces, not duplicates)
- Tab pinning: `find_tab(pattern)` consistently returns the same tab
- z-index: badge > focus > lock > highlight (highest to lowest)
