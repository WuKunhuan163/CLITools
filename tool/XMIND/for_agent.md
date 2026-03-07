# XMIND -- Agent Reference

## Quick Start
```
XMIND boot                    # Boot session (welcome page, then app.xmind.com)
XMIND session                 # State machine status
XMIND status                  # Auth check
XMIND maps                    # List maps
XMIND create "My Map"         # Create map
XMIND open "My Map"           # Open map
```

## API
```python
from tool.XMIND.logic.chrome.api import (
    boot_session, get_auth_state, get_page_info, get_maps,
    get_sidebar, create_map, open_map, get_session_status,
)

# Boot opens dedicated Chrome window with XMind overlays
r = boot_session()

# State machine tracks: IDLE -> VIEWING_HOME -> VIEWING_MAP -> EDITING
s = get_session_status()  # {'state': 'idle', 'last_url': '...', ...}

# Create or open maps via MCP interaction interfaces
create_map("My Map")    # Highlights + clicks 'New Map' button
open_map("My Map")      # Highlights + clicks the map card
```

## State Machine
```python
from tool.XMIND.logic.chrome.state_machine import get_machine, XMState

machine = get_machine("xmind")
print(machine.state)          # XMState.IDLE
print(machine.to_dict())      # Full state with URL, map title, errors
```

State file: `data/state/xmind_default.json`

## Recovery
- Tab closure detected automatically
- Reboots session in new window
- Navigates to last known URL
- Max 3 recovery attempts before reset

## Notes
- No lock overlay (user needs free interaction with XMind)
- Badge color: #f44336 (red), letter "X"
- Requires authenticated app.xmind.com session in Chrome
