# XMIND -- Agent Reference

## Quick Commands

| Command | Description |
|---|---|
| `XMIND boot` | Boot session in dedicated window |
| `XMIND session` | Show session/state status |
| `XMIND status` | Auth state |
| `XMIND page` | Current page info |
| `XMIND maps` | List mind maps |
| `XMIND nodes` | List all visible nodes |
| `XMIND home` | Navigate to home |
| `XMIND create "title"` | Create new map |
| `XMIND open "title"` | Open existing map |
| `XMIND add-node "text" [--parent "X"] [--sibling]` | Add node |
| `XMIND edit-node "old" "new"` | Edit node text |
| `XMIND delete-node "text"` | Delete node |
| `XMIND screenshot [--output path]` | Capture page |

## Python API

```python
from tool.XMIND.logic.chrome.api import (
    boot_session, get_auth_state, get_page_info, get_maps,
    get_sidebar, create_map, open_map, add_node, edit_node,
    delete_node, take_screenshot, navigate_home, get_map_nodes,
    get_session_status,
)
```

## State Machine

States: UNINITIALIZED -> BOOTING -> IDLE -> NAVIGATING -> VIEWING_HOME / VIEWING_MAP -> EDITING

Recovery: max 3 attempts, reboots session and restores last URL.

## Key Selectors

- Topic nodes: `[class*="topic"], [class*="Topic"], [data-type="topic"]`
- Map cards: `[class*="file-card"], [class*="card-item"]`
- New map button: `button[class*="new"], [class*="new-map"]`
