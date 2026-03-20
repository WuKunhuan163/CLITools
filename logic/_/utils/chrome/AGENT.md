# logic/chrome - Agent Reference

## Key Interfaces

### session.py
- `is_chrome_cdp_available(port=9222)` - Check CDP reachable
- `list_tabs(port)` - All targets as list of dicts
- `find_tab(url_pattern, port, tab_type)` - First matching tab with webSocketDebuggerUrl
- `close_tab(target_id, port)`, `open_tab(url, port)`
- `CDPSession(ws_url, timeout)` - `send_and_recv(method, params)`, `send_only(method, params)`, `evaluate(expression)`, `drain()`, `close()`
- `real_click(session, x, y)`, `insert_text(session, text)`, `dispatch_key(session, key, code, key_code, event_type)`
- `capture_screenshot(session, fmt)`, `get_dom_text`, `get_dom_attribute`, `query_selector_all_text`, `fetch_api`

## Requirements

- Chrome with `--remote-debugging-port=9222 --remote-allow-origins=*`
- `websocket-client`

## Gotchas

- `logic.lang.audit_imports` IMP002: Prefer CDMCP `session.require_tab()` over raw find_tab/open_tab
- `send_only` for Input.dispatch* to avoid response wait
- `drain()` clears event buffer after rapid input
