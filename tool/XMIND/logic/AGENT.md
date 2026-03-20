# XMIND Logic — Technical Reference

## Architecture

XMIND is an advanced CDMCP tool using the full session manager:
```
boot_session() -> CDMCP session_manager.create_session()
  -> overlay injection (badge, focus)
  -> XMState FSM tracks lifecycle
  -> chrome/api.py methods operate via CDP
```

## chrome/api.py

Session-based operations (not just tab discovery):
- `boot_session()`: Creates CDMCP session, injects overlays
- `get_auth_state()`, `get_page_info()`: Session status
- Map operations: `get_maps()`, `create_map()`, `open_map()`, `rename_map()`, `export_map()`
- Node operations: `add_node()`, `edit_node()`, `delete_node()`, `copy_node()`, `paste_node()`
- Navigation: `navigate_home()`, `get_sidebar()`, `get_map_nodes()`
- Edit helpers: `undo()`, `redo()`, `zoom()`, `fit_map()`, `select_all()`, `collapse_node()`, `expand_node()`
- `take_screenshot()`, `get_mcp_state()`, `get_session_status()`

## chrome/state_machine.py

`XMState` enum FSM:
- States: UNINITIALIZED, BOOTING, IDLE, NAVIGATING, VIEWING_HOME, VIEWING_MAP, EDITING
- Persists to `data/state/` for cross-process coordination

## Gotchas

1. **Session-based, not tab-based**: Uses `boot_session()` instead of `find_xmind_tab()`. The session must be booted before operations.
2. **State persistence**: State file at `data/state/` — read this to check session status before booting a new one.
