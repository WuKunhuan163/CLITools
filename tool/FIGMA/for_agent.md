# FIGMA -- Agent Reference

## Quick Commands

| Command | Description |
|---|---|
| `FIGMA boot` | Boot session (auto-launches Chrome if needed) |
| `FIGMA session` | Show session/state status |
| `FIGMA status` | Auth state |
| `FIGMA page` | Current page info |
| `FIGMA files` | List design files |
| `FIGMA layers` | List layers in current file |
| `FIGMA home` | Navigate to home |
| `FIGMA open "title"` | Open design file |
| `FIGMA create --type design` | Create new file (design/figjam/slides) |
| `FIGMA screenshot [--output path]` | Capture page |
| `FIGMA editor-info` | Identify editor areas |
| `FIGMA properties` | Read right-panel property values |

## Canvas Operations

Drawing uses `_figma_drag()` with fire-and-forget CDP events -- auto-locks, counts MPC:

| Command | Description |
|---|---|
| `FIGMA rectangle --x N --y N [--width W --height H]` | Draw rectangle |
| `FIGMA ellipse --x N --y N [--width W --height H]` | Draw ellipse |
| `FIGMA line --x1 N --y1 N --x2 N --y2 N` | Draw line |
| `FIGMA frame --x N --y N [--width W --height H]` | Draw frame |
| `FIGMA text "Hello" --x N --y N` | Add text |
| `FIGMA select-all` | Select all (Cmd+A) |
| `FIGMA group` | Group selection (Cmd+G) |
| `FIGMA ungroup` | Ungroup (Cmd+Shift+G) |
| `FIGMA copy` / `FIGMA paste` | Copy/paste |
| `FIGMA duplicate` | Duplicate (Cmd+D) |
| `FIGMA delete` | Delete selection |
| `FIGMA deselect` | Click canvas to deselect |
| `FIGMA move --dx N --dy N` | Move selection |
| `FIGMA resize --width N --height N` | Resize selection |
| `FIGMA rotate --degrees N` | Rotate selection |
| `FIGMA color FF6B6B` | Change fill color (hex without #) |
| `FIGMA stroke --color "#000" --width 2` | Add stroke |
| `FIGMA corner-radius 8` | Set corner radius |
| `FIGMA zoom --level 150` | Set zoom (50-800%) |
| `FIGMA undo` / `FIGMA redo` | Undo/redo |
| `FIGMA rename "New Name"` | Rename file |
| `FIGMA rename-layer "old" "new"` | Rename layer |
| `FIGMA close` | Close file, return home |

## Component System

| Command | Description |
|---|---|
| `FIGMA create-component` | Create component from selection (Cmd+Alt+K) |
| `FIGMA detach-instance` | Detach component instance (Cmd+Alt+B) |
| `FIGMA auto-layout` | Apply auto layout to selection (Shift+A) |

## Panel & Tabs

| Command | Description |
|---|---|
| `FIGMA mode design` | Switch to Design tab |
| `FIGMA mode prototype` | Switch to Prototype tab |
| `FIGMA panel-tab design` | Alternative tab switch |
| `FIGMA comment --text "note" --x 100 --y 200` | Add comment |
| `FIGMA properties` | Read visible property values |

## Menus & Plugins

| Command | Description |
|---|---|
| `FIGMA plugins` | Open main menu -> Plugins (lists available items) |
| `FIGMA quick-actions --query "auto"` | Open Quick Actions (Cmd+/) |
| `FIGMA export` | Open export dialog |
| `FIGMA add-export` | Add export setting to selected element |
| `FIGMA tool --name rectangle` | Switch tool |

## Python API

```python
from tool.FIGMA.logic.chrome.api import (
    boot_session, get_auth_state, get_page_info, list_files,
    open_file, take_screenshot, navigate_home, get_layers,
    get_session_status, get_editor_info, close_file,
    # Drawing
    draw_rectangle, draw_ellipse, draw_line, draw_frame, add_text,
    # Selection
    select_all, group_selection, ungroup_selection,
    copy_selection, paste_selection, duplicate_selection, delete_selection,
    move_selection, resize_selection, rotate_selection,
    click_canvas, deselect,
    # Styling
    change_fill_color, add_stroke, set_corner_radius, zoom,
    # Components
    create_component, detach_instance, auto_layout,
    # Panel
    switch_mode, switch_panel_tab, get_panel_properties,
    rename_layer, add_comment, rename_file,
    # Menus
    open_plugins_menu, open_quick_actions, add_export_setting,
)
```

## State Machine

States: UNINITIALIZED -> BOOTING -> IDLE -> NAVIGATING -> VIEWING_HOME / VIEWING_FILE -> EDITING

Recovery: max 3 attempts, reboots session and restores last URL. Chrome is auto-relaunched if closed.

## Key Implementation Details

- **Fire-and-forget Input**: Keyboard and mouse events use `cdp.send_only()` to avoid
  blocking when Figma's WebGL canvas floods the websocket with rendering events
- **Websocket drain**: `cdp.drain()` clears buffered event noise after mouse drags/clicks
  before subsequent JS evaluations
- **Canvas focus**: Drawing tools require `canvas.focus()` before keyboard activation
- Keyboard shortcuts use CDP `rawKeyDown` + `char` + `keyUp` for WebGL canvas compatibility
- Drawing operations click canvas center and press Escape before tool activation
- `rename_file` clicks canvas after renaming to deselect the filename input
- Right-panel tabs are "Design" and "Prototype" (visible in top-right of editor)
- Main menu accessed via the Figma logo button (top-left SVG icon)
- Plugins submenu shows "Run last plugin" and "Manage plugins..."

## Lessons Learned

1. Figma's WebGL canvas generates massive event floods after mouse drags, blocking
   synchronous CDP responses. Solution: `send_only` for input events + `drain()` after.
2. Click coordinates must be on the canvas (not panels) for tool activation to work.
3. The filename input captures keyboard focus if not explicitly deselected after rename.
4. The right panel tabs are "Design" and "Prototype" (not "Properties"/"Comments" as
   in some earlier Figma versions). These are found via text content match in the DOM.
5. The Figma main menu opens via JS `.click()` on the logo button, not CDP mouse events.
