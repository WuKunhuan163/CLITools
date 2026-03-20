# LUCIDCHART - Lucidchart Diagramming Automation via CDMCP

Automate Lucidchart diagramming tasks through Chrome DevTools Protocol. Built on the CDMCP session infrastructure for authenticated, overlay-locked browser automation.

## Prerequisites

- CDMCP session running (`GOOGLE.CDMCP --mcp-boot`)
- Google account logged in (Lucidchart uses Google SSO)

## Quick Start

```bash
LUCIDCHART --mcp-boot                          # Boot session and open Lucidchart
LUCIDCHART --mcp-status                        # Check auth state
LUCIDCHART --mcp-documents                     # List recent documents
LUCIDCHART --mcp-open-doc "name"               # Open document by title
LUCIDCHART --mcp-add-shape Process --x 500 --y 400  # Add shape
LUCIDCHART --mcp-screenshot --output /tmp/out.png    # Capture
```

## MCP Commands

All MCP commands use the `--mcp-` prefix.

### Session & Status

| Command | Description |
|---------|-------------|
| `--mcp-boot` | Boot Lucidchart in a CDMCP session window |
| `--mcp-session` | Show session and state machine status |
| `--mcp-recover` | Recover from error state |
| `--mcp-status` | Check authentication state (user, plan) |
| `--mcp-page` | Show current page info (URL, title, section) |
| `--mcp-state` | Comprehensive MCP state |
| `--mcp-layout` | Identify editor areas (toolbar, canvas, panels) |

### Navigation

| Command | Description |
|---------|-------------|
| `--mcp-navigate <target>` | Navigate to section or URL (home, documents, templates, recent, shared, trash) |
| `--mcp-back` | Navigate back |
| `--mcp-new` | Create new blank Lucidchart document |
| `--mcp-open <url>` | Open document by URL |
| `--mcp-open-doc <name>` | Open document by title (matches card in documents view) |
| `--mcp-templates [category]` | Browse templates, optionally filtered by category |
| `--mcp-documents [--limit N]` | List documents |

### Editor Operations

| Command | Description |
|---------|-------------|
| `--mcp-select-all` | Select all canvas objects (Cmd+A) |
| `--mcp-delete` | Delete selected objects |
| `--mcp-copy` | Copy selected (Cmd+C) |
| `--mcp-paste` | Paste (Cmd+V) |
| `--mcp-undo` | Undo (Cmd+Z) |
| `--mcp-redo` | Redo (Cmd+Shift+Z) |
| `--mcp-group` | Group selected (Cmd+G) |
| `--mcp-ungroup` | Ungroup selected (Cmd+Shift+G) |
| `--mcp-escape` | Deselect / cancel |
| `--mcp-zoom [level]` | Zoom: in, out, fit, reset |
| `--mcp-zoom-level` | Show current zoom percentage |

### Shape & Drawing

| Command | Description |
|---------|-------------|
| `--mcp-add-shape <name> [--x X --y Y]` | Drag shape from library onto canvas |
| `--mcp-add-text <text> [--x X --y Y]` | Add text block with content |
| `--mcp-click <x> <y>` | Click at canvas coordinates |
| `--mcp-draw-line <x1> <y1> <x2> <y2>` | Draw line between two points |
| `--mcp-fill-color <hex>` | Set fill color for selected object |
| `--mcp-toolbar <title>` | Click a toolbar button by its aria-label |
| `--mcp-rename <name>` | Rename current document |

### Page & Info

| Command | Description |
|---------|-------------|
| `--mcp-pages` | List pages in document |
| `--mcp-add-page` | Add new page |
| `--mcp-shapes` | List available shapes from library |
| `--mcp-shape-libraries` | List shape library sections |

### Utility

| Command | Description |
|---------|-------------|
| `--mcp-screenshot [--output path]` | Capture page screenshot |

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |

## Architecture

- **State Machine**: `LucidState` (UNINITIALIZED, BOOTING, IDLE, NAVIGATING, EDITING, ERROR, RECOVERING)
- **Session**: Uses CDMCP `require_tab()` for tab isolation in session window
- **Overlays**: Badge ("Lucidchart MCP"), favicon, lock overlay with passthrough for interactions
- **Shape Library**: Drag-and-drop from sidebar; shapes identified by `aria-label` attribute
- **Editor**: WebGL canvas; keyboard shortcuts via CDP `Input.dispatchKeyEvent`

## Known Limitations

- Lucidchart opens documents in new tabs; the tool auto-detects editor tabs
- Canvas is WebGL-rendered; DOM-based selection is not available
- `--mcp-select-all` requires canvas focus; use `--mcp-click` on empty area first
- Free plan has limited features (no team library, limited exports)
