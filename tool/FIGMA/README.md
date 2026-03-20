# FIGMA -- Design Automation via CDMCP

Figma design tool automation with CDMCP session management, visual overlays,
MCP interaction interfaces, and Turing machine state tracking.

## Prerequisites

- Google Chrome (auto-launched by CDMCP if closed)
- GOOGLE.CDMCP tool installed
- Figma account signed in on the Chrome debug profile

## Features

- **Session management**: Dedicated Chrome window for Figma via CDMCP
- **Tab pinning**: Session tab pinned automatically
- **Visual overlays**: Badge (Figma MCP), focus border, lock, cursor tracking, favicon
- **State machine**: IDLE -> NAVIGATING -> VIEWING_HOME / VIEWING_FILE -> EDITING
- **Recovery**: Detects tab closure and reboots automatically (including Chrome restart)
- **Canvas operations**: Draw, select, group, move, color, export via MPC-tracked interactions
- **Component system**: Create components, instances, variants, auto-layout
- **Panel navigation**: Switch between Design/Prototype tabs, read properties
- **Plugin access**: Open Figma main menu and plugins submenu
- **Quick Actions**: Search Figma commands via Cmd+/

## MCP Commands

All MCP commands use the `--mcp-` prefix.

### Session & Info

```bash
FIGMA --mcp-boot                         # Boot Figma session in dedicated window
FIGMA --mcp-session                      # Show session + state machine status
FIGMA --mcp-recover                      # Manual recovery
FIGMA --mcp-status                       # Authentication state
FIGMA --mcp-page                         # Current page info
FIGMA --mcp-files                        # List design files
FIGMA --mcp-layers                       # List layers in current file
FIGMA --mcp-editor-info                  # Identify editor areas (canvas, panels)
FIGMA --mcp-properties                   # Read right-panel property values
```

### Navigation

```bash
FIGMA --mcp-home                         # Go to Figma home
FIGMA --mcp-open "My Design"             # Open a design file
FIGMA --mcp-create --type design         # Create new file (design/figjam/slides)
FIGMA --mcp-close                        # Close file and return to home
```

### Canvas Drawing

```bash
FIGMA --mcp-rectangle --x 100 --y 100 --width 200 --height 150
FIGMA --mcp-ellipse --x 300 --y 100 --width 100 --height 100
FIGMA --mcp-line --x1 50 --y1 50 --x2 250 --y2 200
FIGMA --mcp-frame --x 100 --y 100 --width 400 --height 300
FIGMA --mcp-text "Hello World" --x 150 --y 250
```

### Selection & Manipulation

```bash
FIGMA --mcp-select-all                   # Select all objects (Cmd+A)
FIGMA --mcp-group                        # Group selection (Cmd+G)
FIGMA --mcp-ungroup                      # Ungroup selection (Cmd+Shift+G)
FIGMA --mcp-copy                         # Copy selection (Cmd+C)
FIGMA --mcp-paste                        # Paste (Cmd+V)
FIGMA --mcp-duplicate                    # Duplicate (Cmd+D)
FIGMA --mcp-delete                       # Delete selection (Backspace)
FIGMA --mcp-deselect                     # Click canvas to deselect
```

### Components

```bash
FIGMA --mcp-create-component             # Create component from selection (Cmd+Alt+K)
FIGMA --mcp-detach-instance              # Detach component instance (Cmd+Alt+B)
FIGMA --mcp-auto-layout                  # Apply auto layout to selection (Shift+A)
```

### Transform

```bash
FIGMA --mcp-move --dx 50 --dy 0          # Move selection by delta
FIGMA --mcp-color FF6B6B                 # Change fill color (hex without #)
FIGMA --mcp-resize --width 200 --height 150  # Resize selection
FIGMA --mcp-rotate --degrees 45          # Rotate selection
FIGMA --mcp-stroke --color "#000000" --width 2  # Add/modify stroke
FIGMA --mcp-corner-radius 8              # Set corner radius
FIGMA --mcp-zoom --level 150             # Set zoom (50-800%)
```

### Edit

```bash
FIGMA --mcp-undo                         # Undo (Cmd+Z)
FIGMA --mcp-redo                         # Redo (Cmd+Shift+Z)
FIGMA --mcp-rename "New Name"            # Rename current file
FIGMA --mcp-rename-layer "old" "new"     # Rename a layer by name
FIGMA --mcp-export                       # Open export dialog
FIGMA --mcp-add-export                   # Add export setting to selection
```

### Panel & Comments

```bash
FIGMA --mcp-mode design                  # Switch right-panel tab (design/prototype)
FIGMA --mcp-panel-tab prototype          # Alternative panel tab switch
FIGMA --mcp-comment --text "note" --x 100 --y 200  # Add comment at position
```

### Tools & Menus

```bash
FIGMA --mcp-tool --name move             # Switch tools: move/frame/rectangle/ellipse/line/text/hand
FIGMA --mcp-plugins                      # Open plugins menu
FIGMA --mcp-quick-actions --query "auto" # Open Quick Actions with search query
```

### Utility

```bash
FIGMA --mcp-screenshot                   # Save screenshot
FIGMA --mcp-screenshot --output /tmp/x.png
FIGMA --mcp-click --x 400 --y 300        # Click at canvas position
FIGMA --mcp-click --x 400 --y 300 --double  # Double-click
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |

## Canvas Interaction Model

Drawing operations use a Figma-specific drag helper (`_figma_drag`) that wraps
raw CDP input events with auto-locking and MPC counting. Input events (keyboard
and mouse) use fire-and-forget (`send_only`) to avoid blocking when Figma's
WebGL canvas floods the CDP websocket with rendering events.

## State Machine States

| State | Description |
|-------|-------------|
| UNINITIALIZED | No session started |
| BOOTING | Opening Chrome window (includes Chrome relaunch if needed) |
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
