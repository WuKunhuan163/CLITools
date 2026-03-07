# XMIND -- Agent Reference

## Quick Commands

| Command | Description |
|---|---|
| `XMIND boot` | Boot session in dedicated window |
| `XMIND session` | Show session/state status |
| `XMIND status` | Auth state |
| `XMIND state` | Full MCP state (nodes, zoom, URL, title) |
| `XMIND page` | Current page info |
| `XMIND maps` | List mind maps |
| `XMIND nodes` | List all visible nodes |
| `XMIND home` | Navigate to home |
| `XMIND create "title"` | Create new map |
| `XMIND open "title"` | Open existing map |
| `XMIND add-node "text" [--parent "X"] [--sibling]` | Add node |
| `XMIND edit-node "old" "new"` | Edit node text |
| `XMIND delete-node "text"` | Delete node |
| `XMIND rename "new name"` | Rename current map |
| `XMIND undo` | Undo last action |
| `XMIND redo` | Redo last undone action |
| `XMIND fit` | Zoom to fit map |
| `XMIND zoom fit\|actual` | Zoom control |
| `XMIND export png\|pdf\|markdown\|svg\|word\|excel\|powerpoint\|opml` | Export map |
| `XMIND insert note\|todo\|task\|label\|hyperlink\|callout\|comment "text" --node "X"` | Insert item |
| `XMIND copy-node "text"` | Copy node |
| `XMIND paste-node` | Paste copied node |
| `XMIND select-all` | Select all nodes |
| `XMIND collapse "text"` | Toggle collapse/expand |
| `XMIND screenshot [--output path]` | Capture page |

## Python API

```python
from tool.XMIND.logic.chrome.api import (
    boot_session, get_auth_state, get_page_info, get_maps,
    get_sidebar, create_map, open_map, add_node, edit_node,
    delete_node, take_screenshot, navigate_home, get_map_nodes,
    get_session_status, undo, redo, zoom, export_map, insert_item,
    rename_map, fit_map, get_mcp_state, select_all, copy_node,
    paste_node, collapse_node,
)
```

## State Machine

States: UNINITIALIZED -> BOOTING -> IDLE -> NAVIGATING -> VIEWING_HOME / VIEWING_MAP -> EDITING

Recovery: max 3 attempts, reboots session and restores last URL.

## Key Selectors

- Topic nodes: `foreignObject div`, `foreignObject span` (XMind renders in SVG foreignObject)
- Map cards: `[class*="file-card"], [class*="card-item"]`
- Create new: `button` containing "Create New" text
- Hamburger menu: Button at (16,10) 32x32
- Menu items: Hover to reveal submenus (File, Edit, View, Export As)
- Insert dropdown: Button at (567,7) — Zone, Note, To-Do, Task, Hyperlink, Callout, Label, Comment, Image, Equation

## Hamburger Menu Structure

- **File**: New Map, New Sheet, Rename, Add to Starred, Duplicate, Version History, Import File, Download
- **Edit**: Undo, Redo, Search
- **View**: Actual Size, Fit Map, Show Branch Only, Gantt Chart, Pitch Mode, Navigation Panel, Format Panel, Toolbar
- **Export As**: PNG, JPEG, SVG, PDF, Markdown, Word, Excel, PowerPoint (Pitch), Pitch Video, OPML, TextBundle, Excel (Task)
- **Share**, **Shortcuts**, **Print**, **Feedback**

## Toolbar Buttons (x positions from left)

| x | Label | ID |
|---|---|---|
| 243 | Topic | — |
| 295 | Subtopic | — |
| 382 | Relationship | — |
| 452 | Boundary | — |
| 514 | Summary | — |
| 567 | Insert (+) | task-onboarding-toolbar-add-bu |
| 640 | AI | tool-bar-grow-ideas-button |
| 815 | Share | onboarding-step-share |
| 903 | Gantt | task-onboarding-gantt-button |
| 947 | Pitch | — |
| 1001 | Comment | — |
| 1058 | Marker | — |
| 1108 | Format | — |

## Keyboard Shortcuts

- `Tab`: Add child topic
- `Enter`: Add sibling topic / Confirm edit
- `Backspace/Delete`: Delete selected node
- `Cmd+Z`: Undo
- `Cmd+Shift+Z`: Redo
- `Cmd+A`: Select all
- `Cmd+C`: Copy
- `Cmd+V`: Paste
- `/`: Toggle collapse/expand
- Double-click: Enter edit mode on node
