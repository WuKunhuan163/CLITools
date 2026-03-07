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
- **Node manipulation**: Add, edit, delete, copy, paste nodes
- **Export**: PNG, JPEG, SVG, PDF, Markdown, Word, Excel, PowerPoint, OPML
- **Undo/Redo**: Full undo/redo support
- **Zoom control**: Fit to view, actual size
- **Insert items**: Note, To-Do, Task, Hyperlink, Callout, Label, Comment, etc.
- **MCP state reporting**: Full map state query (nodes, zoom, URL, title)
- **Screenshot**: Capture current mind map state

## CLI Usage

```bash
# Session
XMIND boot                         # Boot XMind session in dedicated window
XMIND session                      # Show session + state machine status
XMIND recover                      # Manual recovery

# Info
XMIND status                       # Authentication state
XMIND page                         # Current page info
XMIND maps                         # List mind maps
XMIND sidebar                      # Sidebar sections
XMIND nodes                        # List all visible nodes in current map
XMIND state                        # Full MCP state (nodes, zoom, URL, etc.)

# Navigation
XMIND home                         # Go to home/recents page
XMIND create "My Map"              # Create a new mind map
XMIND open "My Map"                # Open existing mind map

# Editing
XMIND add-node "Topic A"                    # Add child to selected node
XMIND add-node "Topic B" --parent "Root"    # Add child to "Root" node
XMIND add-node "Topic C" --sibling          # Add sibling instead of child
XMIND edit-node "Old Text" "New Text"       # Edit a node's text
XMIND delete-node "Topic A"                 # Delete a node
XMIND rename "New Map Name"                 # Rename the current map

# Clipboard
XMIND copy-node "Topic A"                   # Copy node
XMIND paste-node                             # Paste copied node
XMIND select-all                             # Select all nodes

# Structure
XMIND collapse "Main Topic 1"               # Collapse/expand branch
XMIND insert boundary --node "Topic A"      # Add boundary around node
XMIND insert note "My note" --node "Topic"  # Add note to node
XMIND insert todo --node "Topic A"          # Add to-do checkbox
XMIND insert label "v1.0" --node "Topic"    # Add label to node
XMIND insert hyperlink "https://..." --node "Topic"  # Add link

# View
XMIND fit                          # Zoom to fit entire map
XMIND zoom fit                     # Same as above
XMIND zoom actual                  # Zoom to 100%

# Undo / Redo
XMIND undo                         # Undo last action
XMIND redo                         # Redo last undone action

# Export
XMIND export png                   # Export as PNG (opens dialog)
XMIND export pdf                   # Export as PDF
XMIND export markdown              # Export as Markdown
XMIND export svg                   # Export as SVG
XMIND export word                  # Export as Word
XMIND export excel                 # Export as Excel
XMIND export powerpoint            # Export as PowerPoint
XMIND export opml                  # Export as OPML

# Utility
XMIND screenshot                   # Save screenshot
XMIND screenshot --output /tmp/x.png
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
