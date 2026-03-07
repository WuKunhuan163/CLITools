# FIGMA -- Design Automation via CDMCP

Figma design tool automation with CDMCP session management, visual overlays,
MCP interaction interfaces, and Turing machine state tracking.

## Prerequisites

- Chrome with `--remote-debugging-port=9222` and an authenticated `figma.com` session
- GOOGLE.CDMCP tool installed

## Features

- **Session management**: Dedicated Chrome window for Figma via CDMCP
- **Tab pinning**: Session tab pinned automatically
- **Visual overlays**: Badge (Figma MCP), focus border, favicon
- **State machine**: IDLE -> NAVIGATING -> VIEWING_HOME / VIEWING_FILE -> EDITING
- **Recovery**: Detects tab closure and reboots automatically

## CLI Usage

```bash
# Session
FIGMA boot                         # Boot Figma session in dedicated window
FIGMA session                      # Show session + state machine status
FIGMA recover                      # Manual recovery

# Info
FIGMA status                       # Authentication state
FIGMA page                         # Current page info
FIGMA files                        # List design files
FIGMA layers                       # List layers in current file

# Navigation
FIGMA home                         # Go to Figma home
FIGMA open "My Design"             # Open a design file

# Utility
FIGMA screenshot                   # Save screenshot
FIGMA screenshot --output /tmp/x.png
```

## State Machine States

| State | Description |
|-------|-------------|
| UNINITIALIZED | No session started |
| BOOTING | Opening Chrome window |
| IDLE | Session active, ready |
| NAVIGATING | Moving between pages |
| VIEWING_HOME | On files/home page |
| VIEWING_FILE | Viewing a design file |
| EDITING | Editing file content |
| ERROR | Error occurred |
| RECOVERING | Attempting recovery |

## Dependencies

- GOOGLE.CDMCP (session management, overlays, interaction interfaces)
- websocket-client
