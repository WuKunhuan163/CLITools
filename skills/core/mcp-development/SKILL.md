---
name: mcp-development
description: Guide for developing MCP (browser automation) tools using CDMCP interfaces, including session management, locking, overlays, and interaction patterns.
---

# MCP Development Guide

## Overview

MCP (Model Context Protocol) tools use Chrome DevTools Protocol (CDP) via CDMCP to automate web applications. Each CDMCP tool targets a specific web service (e.g., Gmail, Asana, WhatsApp).

## Architecture

```
tool/<SERVICE>/
    main.py                        # ToolBase + CLI entry point
    logic/cdp/
        session_manager.py         # Tab lifecycle, window management
        <service>_operations.py    # Service-specific CDP operations
    logic/chrome/
        api.py                     # High-level API (screenshot, auth)
    interface/main.py              # Cross-tool public API
```

## Session Management

```python
from tool.GOOGLE.CDMCP.logic.cdp.session_manager import CDMCPSession

session = CDMCPSession.get_or_create("my_service")
tab = session.require_tab(
    label="main",
    url="https://example.com",
    url_pattern="example.com",
    locked=True,
)
```

### Key Methods
- `require_tab(label, url, url_pattern)` -- Get or create a managed tab
- `register_tab(label, tab_id, url, ws)` -- Register an external tab
- `full_reboot(skip_demo=False)` -- Recreate session window and tabs

## Tab Lifecycle

1. **Created** via `require_tab` or `open_tab_in_session`
2. **Locked** by default (user cannot interact)
3. **Unlocked** when user interaction needed
4. **Closed** explicitly or on session teardown

## Overlays

Visual indicators injected into managed tabs:

```python
from tool.GOOGLE.CDMCP.logic.cdp.overlays import (
    inject_lock, remove_lock,
    inject_badge, inject_tip,
    inject_focus, inject_highlight,
)
```

| Overlay | Purpose |
|---------|---------|
| Lock | Prevents user interaction, shows "Locked by Terminal Tool" |
| Badge | Small label (e.g., "CDMCP Auth") in corner |
| Tip | Blue banner at top with instructions |
| Focus | Border highlight on a DOM element |
| Highlight | Temporary flash effect |

## Screenshots

Always hide overlays before capturing:

```python
from tool.GOOGLE.CDMCP.logic.chrome.api import screenshot_tab
screenshot_tab(session, tab_id, path="/tmp/screenshot.png")
```

## Turing Machine State Considerations

When developing MCP commands, verify precondition state:

| State | How to Check | Recovery |
|-------|-------------|----------|
| Chrome running | `is_chrome_cdp_available()` | `ensure_chrome()` |
| Session exists | `CDMCPSession.get_or_create()` | Auto-creates |
| Tab alive | `session.is_tab_alive(tab_id)` | `require_tab()` |
| User logged in | `check_auth_cookies(verify=True)` | `initiate_login()` |

### Authentication-Gated Commands

Commands requiring login must check auth state first:

```python
verified = auth.check_auth_cookies(cdp, verify=True)
if not verified.get("signed_in"):
    print("  Login required. Run: CDMCP --mcp-login")
    return
```

## Guidelines

1. Always use `require_tab` -- never raw `Target.createTarget`
2. Lock tabs by default; only unlock for user interaction
3. Hide overlays before screenshots
4. Check auth state before service-specific operations
5. Close temporary tabs in `finally` blocks
6. Use `_validate_session_tabs()` during development for state checks
