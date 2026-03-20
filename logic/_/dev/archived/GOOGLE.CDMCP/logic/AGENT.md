# GOOGLE.CDMCP Logic — Technical Reference

## Architecture

CDMCP provides the foundational browser automation layer. All CDMCP-based tools (WHATSAPP, GMAIL, WPS, etc.) depend on this tool for session management and CDP operations.

```
CDMCP tool child (e.g. WHATSAPP)
  -> chrome/api.py (high-level API)
    -> cdp/session_manager.py (named sessions, lifetime tabs)
    -> cdp/interact.py (click/type/scroll with overlay highlighting)
    -> cdp/overlay.py (CSS/JS injection for visual cues)
    -> cdp/server.py (persistent HTTP server for welcome page + auth API)
```

## cdp/ Package — Core CDP Operations

### session_manager.py
Manages named sessions, each with a dedicated Chrome tab:
- `create_session(name, url)`: Opens a tab and registers the session
- `get_session(name)`: Returns tab info for a named session
- `close_session(name)`: Closes tab and deregisters
- Sessions persist across tool invocations via state file

### interact.py
High-level interaction patterns combining overlay + action:
1. Highlight target element with overlay
2. Execute CDP action (click, type, scroll)
3. Remove highlight
Each operation includes configurable delay for visual effect.

### overlay.py
Visual indicator system via `Runtime.evaluate`:
- **Tab badge**: Persistent label marking agent-controlled tabs
- **Focus indicator**: Border glow on active debug tab
- **Element highlight**: Temporary colored border on interacted elements
- **Lock overlay**: Full-page overlay during locked sessions

Overlay IDs: `CDMCP_OVERLAY_ID`, `CDMCP_LOCK_ID`, `CDMCP_BADGE_ID`, `CDMCP_FOCUS_ID`, `CDMCP_HIGHLIGHT_ID`

### server.py / server_standalone.py
Persistent HTTP background server:
- Serves welcome page with live connection status
- Exposes Google auth API (cookie-based checks)
- State file at `data/cdmcp_server.json` (PID, port)
- `server_standalone.py` is the entry point for the background process

### google_auth.py
Lightweight Google authentication monitoring:
- Cookie-based auth check (no rate limits, unlike API calls)
- Background thread updates welcome page ACCOUNT status card

### google_myaccount.py
Google My Account page automation:
- Personal Info extraction (name, email, phone, birthday)
- Security info (2FA, devices, recent activity)

### demo.py / demo_state.py
Continuous automated demo mode:
- Cycles through contacts with randomized timing
- `DemoStateMachine`: FSM tracking boot → running → waiting → relock → error

## chrome/ Package — High-Level API

### api.py
Unified interface combining tab management + overlays + element interaction:
- Privacy-aware navigation (masks sensitive URLs)
- Tab group management for agent-controlled tabs
- Element operations (click, type, scroll) with built-in visual feedback

## Session Recovery

When a CDMCP session breaks (tab closed, Chrome restarted, WebSocket disconnected):

1. **Check Chrome is running**: `is_chrome_cdp_available()` — if False, prompt user to restart Chrome with `--remote-debugging-port=9222`
2. **Re-find or re-open tab**: For session-based tools, call `boot_session()` again. For tab-based tools, call `find_*_tab()` to locate the tab
3. **Re-inject overlays**: After re-finding a tab, overlays may be lost. The session manager handles this automatically on `create_session()`
4. **Retry the failed operation**: Most operations are idempotent and safe to retry

Common causes of session loss:
- User manually closed the tab
- Chrome crashed or was restarted
- macOS sleep/wake cycle dropped WebSocket connections
- Network interruption on remote Chrome instances

## Rate Limiting

CDMCP operations that interact with web apps should include delays:
- **Between page navigations**: 1-2 seconds (allow page load)
- **Between form fills**: 0.5-1 second (allow UI updates)
- **Between bulk messages**: 2-5 seconds (avoid platform rate limits)
- **After auth checks**: 1 second (allow cookie propagation)

Platform-specific limits:
- **WhatsApp**: Max ~200 messages/day for new numbers. Add 3-5s delay between sends
- **Gmail**: Max ~500 emails/day. Add 1-2s delay between sends
- **LinkedIn/Facebook**: Very aggressive rate limiting. Add 5-10s delays

## Gotchas

1. **Overlay code**: `cdp/overlay.py` is the tool-local overlay implementation. Root `logic/cdp/overlay` provides shared overlay constants. Import directly from `logic.cdp.overlay` when using shared constants.
2. **`_run_demo_bg.py`**: Background demo launcher — hardcodes `/Applications/AITerminalTools` in `sys.path`. If project path changes, this file needs updating.
3. **mcp/ is empty**: MCP protocol handling is done at root `logic/mcp/`, not here.
4. **Server state file**: Located at `data/cdmcp_server.json`. Read this to discover running server PID/port rather than spawning a new one.
