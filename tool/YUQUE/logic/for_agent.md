# YUQUE Logic — Technical Reference

## Architecture

Session-based CDMCP tool (like XMIND/CHARTCUBE):
```
boot_session() -> boot_tool_session() -> require_tab -> CDPSession(ws)
```

CDPSession is cached to avoid multiple WebSocket connections.

## chrome/api.py

- `boot_session()`: Creates CDMCP session for yuque.com with overlays
- `get_status()`: Returns session status and auth state
- `get_page_info()`: Page title, URL, content metadata
- `scan_elements()`: DOM element discovery for interaction

## Gotchas

1. **Session-based**: Uses `boot_session()` + cached `CDPSession`, not simple `find_tab()`.
2. **Early stage**: Limited API — mainly page inspection and element scanning.
