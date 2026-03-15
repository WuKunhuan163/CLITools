# XMIND -- Mind Mapping via CDMCP

XMind mind mapping tool with CDMCP session management, visual overlays,
MCP interaction interfaces, and Turing machine state tracking.

## Prerequisites

- Chrome with `--remote-debugging-port=9222` and an authenticated `app.xmind.com` session
- GOOGLE.CDMCP tool installed

## Features

- **Session management**: Dedicated Chrome window for XMind via CDMCP
- **Visual overlays**: Badge (XMind MCP), focus border, favicon
- **State machine**: IDLE -> NAVIGATING -> VIEWING_HOME -> VIEWING_MAP -> EDITING
- **Recovery**: Detects tab closure and reboots automatically
- **Node manipulation**: Add, edit, delete, copy, paste nodes
- **Export**: PNG, JPEG, SVG, PDF, Markdown, Word, Excel, PowerPoint, OPML
- **MCP state reporting**: Full map state query (nodes, zoom, URL, title)

## MCP Commands

All MCP commands use the `--mcp-` prefix.

### Session & Info
```bash
XMIND --mcp-boot                         # Boot XMind session in dedicated window
XMIND --mcp-session                      # Show session + state machine status
XMIND --mcp-recover                      # Manual recovery
XMIND --mcp-status                       # Authentication state
XMIND --mcp-page                         # Current page info
XMIND --mcp-state                        # Full MCP state
XMIND --mcp-maps                         # List mind maps
XMIND --mcp-nodes                        # List all visible nodes
```

### Navigation
```bash
XMIND --mcp-home                         # Go to home/recents page
XMIND --mcp-create "My Map"              # Create a new mind map
XMIND --mcp-open "My Map"                # Open existing mind map
```

### Editing
```bash
XMIND --mcp-add-node "Topic A"                    # Add child to selected
XMIND --mcp-add-node "Topic B" --parent "Root"    # Add child to "Root"
XMIND --mcp-add-node "Topic C" --sibling          # Add sibling
XMIND --mcp-edit-node "Old Text" "New Text"       # Edit node text
XMIND --mcp-delete-node "Topic A"                 # Delete node
XMIND --mcp-rename "New Map Name"                 # Rename map
XMIND --mcp-copy-node "Topic A"                   # Copy node
XMIND --mcp-paste-node                            # Paste node
XMIND --mcp-select-all                            # Select all
```

### Structure
```bash
XMIND --mcp-collapse "Main Topic 1"               # Collapse/expand branch
XMIND --mcp-insert boundary --node "Topic A"      # Add boundary
XMIND --mcp-insert note "My note" --node "Topic"  # Add note
XMIND --mcp-insert todo --node "Topic A"          # Add to-do checkbox
```

### View & Export
```bash
XMIND --mcp-fit                          # Zoom to fit
XMIND --mcp-zoom fit|actual              # Zoom control
XMIND --mcp-undo                         # Undo
XMIND --mcp-redo                         # Redo
XMIND --mcp-export png|pdf|markdown|svg  # Export map
XMIND --mcp-screenshot [--output path]   # Capture screenshot
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |

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
| ERROR | Error occurred |
| RECOVERING | Attempting recovery |

## Dependencies

- GOOGLE.CDMCP (session management, overlays, interaction interfaces)
- websocket-client
