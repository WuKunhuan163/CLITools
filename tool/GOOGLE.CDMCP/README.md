# GOOGLE.CDMCP — Chrome DevTools MCP

Visual browser automation tool with tab management, overlay indicators, and privacy configuration. Provides agent-level control over Chrome tabs via CDP (Chrome DevTools Protocol).

## Prerequisites

- Chrome/Chromium running with `--remote-debugging-port=9222 --remote-allow-origins=*`
- Python `websocket-client` package

## Features

### 1. Tab Group Badge
Persistent tag in the top-right corner marking agent-controlled tabs. All debug tabs are visually identified.

### 2. Focus Indicator
Subtle blue border around the viewport edge when the agent is actively watching a tab.

### 3. Lock Overlay
Semi-transparent gray shade over the page when the agent is interacting:
- Light shade (`rgba(0,0,0,0.08)`) during normal lock
- Flash darker on user click attempt (`rgba(0,0,0,0.25)` for 300ms)
- Centered "Click to unlock" label that users can click to dismiss

### 4. Element Highlight
Orange outline around the targeted element with a label tag. Returns element metadata including tag, type, name, placeholder, aria-label, and bounding rect.

## CLI Usage

```bash
CDMCP status                                 # Check Chrome CDP availability
CDMCP navigate https://example.com           # Open URL with overlays
CDMCP focus example.com                      # Set focus on matching tab
CDMCP lock example.com                       # Lock tab with overlay
CDMCP unlock example.com                     # Remove lock
CDMCP highlight example.com "input[name=q]" --label "Search box"
CDMCP clear example.com                      # Remove highlight
CDMCP cleanup example.com                    # Remove all overlays
CDMCP config                                 # Show configuration
CDMCP config --set allow_oauth_windows true  # Set config value
CDMCP config --reset                         # Reset to defaults
CDMCP tabs                                   # List managed tabs
```

## Privacy Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `allow_oauth_windows` | `true` | Allow OAuth popups (Cursor IDE blocks these by default) |
| `allow_navigation_outside_domain` | `true` | Allow agent to navigate outside initial domain |
| `block_file_downloads` | `false` | Block agent-triggered file downloads |
| `screenshot_redact_sensitive` | `false` | Redact sensitive fields in screenshots |
| `log_interactions` | `true` | Log interactions to `data/report/interaction_log.txt` |

## Python API

```python
from logic.cdp.overlay import (
    get_session_for_url,
    inject_badge, inject_focus, inject_lock,
    inject_highlight, remove_all_overlays,
)

session = get_session_for_url("example.com")
inject_badge(session, text="CDMCP", color="#1a73e8")
inject_focus(session)
inject_lock(session, base_opacity=0.08, flash_opacity=0.25)
result = inject_highlight(session, "h1", label="Main Heading")
# result: {ok: true, selector: "h1", element: {tag, type, ...}, rect: {...}}
remove_all_overlays(session)
session.close()
```

## Testing

```bash
python3 tool/GOOGLE.CDMCP/test/test_00_help.py -v      # Help test
python3 tool/GOOGLE.CDMCP/test/test_01_overlay_visual.py -v  # 20 overlay tests
python3 tool/GOOGLE.CDMCP/test/test_02_full_workflow.py -v    # Lifecycle test
```
