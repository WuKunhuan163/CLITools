# GOOGLE.CDMCP Logic

Chrome DevTools MCP — the session management backbone for all Chrome-based tools. Manages named browser sessions, visual overlays, tab lifecycles, and interaction interfaces.

## Structure

| Module | Purpose |
|--------|---------|
| `tutorial/setup_guide.py` | Interactive setup wizard |

## Sub-Packages

| Directory | Purpose |
|-----------|---------|
| `cdp/` | Core CDP operations — sessions, server, auth, interactions, overlays, demo |
| `chrome/` | High-level browser API — tab management, element ops, privacy-aware navigation |
| `mcp/` | MCP protocol layer (empty, handled at root level) |
| `translation/` | Localized strings (zh.json) |

## Hierarchy

```
chrome/api.py (high-level: tab + overlay + element ops)
  -> cdp/session_manager.py (session lifecycle)
  -> cdp/interact.py (MCP interaction interfaces)
  -> cdp/overlay.py (visual overlay injection)
  -> cdp/server.py (persistent HTTP server)
  -> cdp/google_auth.py (Google account auth monitoring)
```
