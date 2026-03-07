# FIGMA -- Agent Reference

## Quick Commands

| Command | Description |
|---|---|
| `FIGMA boot` | Boot session in dedicated window |
| `FIGMA session` | Show session/state status |
| `FIGMA status` | Auth state |
| `FIGMA page` | Current page info |
| `FIGMA files` | List design files |
| `FIGMA layers` | List layers in current file |
| `FIGMA home` | Navigate to home |
| `FIGMA open "title"` | Open design file |
| `FIGMA screenshot [--output path]` | Capture page |

## Python API

```python
from tool.FIGMA.logic.chrome.api import (
    boot_session, get_auth_state, get_page_info, list_files,
    open_file, take_screenshot, navigate_home, get_layers,
    get_session_status,
)
```

## State Machine

States: UNINITIALIZED -> BOOTING -> IDLE -> NAVIGATING -> VIEWING_HOME / VIEWING_FILE -> EDITING

Recovery: max 3 attempts, reboots session and restores last URL.
