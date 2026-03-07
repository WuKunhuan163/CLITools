# XMIND -- Mind Mapping via CDMCP

XMind mind mapping tool with CDMCP session management, visual overlays,
MCP interaction interfaces, and Turing machine state tracking.

## Prerequisites

- Chrome with `--remote-debugging-port=9222` and an authenticated `app.xmind.com` session
- GOOGLE.CDMCP tool installed

## Features

- **Session management**: Dedicated Chrome window for XMind via CDMCP
- **Welcome page**: Shows on session boot before navigating to XMind
- **Tab pinning**: Session tab is pinned automatically
- **Visual overlays**: Badge (XMind MCP), focus border, favicon
- **State machine**: Tracks IDLE -> NAVIGATING -> VIEWING_HOME -> VIEWING_MAP -> EDITING
- **State persistence**: `data/state/xmind_default.json`
- **Recovery**: Detects tab closure and reboots automatically

## CLI Usage

```bash
XMIND boot                    # Boot XMind session in dedicated window
XMIND session                 # Show session + state machine status
XMIND status                  # Authentication state
XMIND page                    # Current page info
XMIND maps                    # List mind maps
XMIND sidebar                 # Sidebar sections
XMIND create "My Map"         # Create a new mind map
XMIND open "My Map"           # Open existing mind map
XMIND recover                 # Manual recovery
```

## State Machine States

| State | Description |
|-------|-------------|
| UNINITIALIZED | No session started |
| BOOTING | Opening Chrome window |
| IDLE | Session active, ready |
| NAVIGATING | Moving between pages |
| VIEWING_HOME | On home/recents page |
| VIEWING_MAP | Viewing a mind map |
| EDITING | Editing map content |
| CREATING | Creating new map |
| EXPORTING | Exporting map |
| ERROR | Error occurred |
| RECOVERING | Attempting recovery |

## Dependencies

- GOOGLE.CDMCP (session management, overlays, interaction interfaces)
- websocket-client
