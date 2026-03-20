# FIGMA Logic — Technical Reference

## Architecture

Advanced CDMCP tool with session manager + state machine:
```
boot_session() -> CDMCP session for figma.com
  -> State machine tracks lifecycle
  -> chrome/api.py (50 methods)
```

## chrome/api.py

Public API: `boot_session()`, `get_auth_state()`, `get_page_info()`, `list_files()`, `open_file()`, `take_screenshot()`, `navigate_home()`, `get_layers()`, `get_session_status()`, `create_file()`, and 40 more.

## chrome/state_machine.py

FSM with crash recovery:
- Persists state to `data/state/` for cross-process coordination
- Detects tab closure and triggers automatic recovery

## Gotchas

1. **Session-based**: Uses `boot_session()`, not simple `find_tab()`.
2. **State persistence**: Check `data/state/` before booting a new session.
3. **CDP port**: Requires Chrome with `--remote-debugging-port=9222`.
