# GOOGLE.GS Logic — Technical Reference

## Architecture

Advanced CDMCP tool with session manager + state machine:
```
boot_session() -> CDMCP session for scholar.google.com
  -> State machine tracks lifecycle
  -> chrome/api.py (17 methods)
```

## chrome/api.py

Public API: `boot_session()`, `get_mcp_state()`, `search()`, `get_results()`, `next_page()`, `prev_page()`, `open_paper()`, `filter_time()`, `filter_sort()`, `save_paper()`, and 7 more.

## chrome/state_machine.py

FSM with crash recovery:
- Persists state to `data/state/` for cross-process coordination
- Detects tab closure and triggers automatic recovery

## Gotchas

1. **Session-based**: Uses `boot_session()`, not simple `find_tab()`.
2. **State persistence**: Check `data/state/` before booting a new session.
3. **CDP port**: Requires Chrome with `--remote-debugging-port=9222`.
