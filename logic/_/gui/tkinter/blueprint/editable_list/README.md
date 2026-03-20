# GUI Blueprint: editable_list

A reorderable list manager GUI with Cancel/Save bottom bar.

## Dependency Chain

```
BaseGUIWindow (base.py)
    -> BottomBarWindow (bottom_bar/gui.py)
        -> EditableListWindow (editable_list/gui.py)
```

## Features

- Numbered list display (0-indexed).
- Move Up / Move Down / Move to Top / Move to Bottom sidebar buttons.
- Add / Edit / Delete operations (toggleable via constructor flags).
- Cancel / Save bottom bar from `BottomBarWindow`.
- External control commands for programmatic testing and automation.

## External Control Commands

These methods can be called directly on an `EditableListWindow` instance for testing:

| Method | Description |
|--------|-------------|
| `cmd_select(index)` | Select item at 0-based index. |
| `cmd_move_up()` | Move selected item up. |
| `cmd_move_down()` | Move selected item down. |
| `cmd_move_to_top()` | Move selected item to top. |
| `cmd_move_to_bottom()` | Move selected item to bottom. |
| `cmd_add(text)` | Append a new item. |
| `cmd_edit(index, text)` | Replace item at index. |
| `cmd_delete(index)` | Remove item at index. |
| `cmd_get_items()` | Return current list of items. |
| `cmd_save()` | Trigger save action. |
| `cmd_cancel()` | Trigger cancel action. |

## Usage

```python
from logic._.gui.tkinter.blueprint.editable_list.gui import EditableListWindow

win = EditableListWindow(
    title="Manage Queue",
    internal_dir=str(logic_dir),
    tool_name="MY_TOOL",
    items=["Task 1", "Task 2", "Task 3"],
    list_label="Queued prompts:",
)
win.run()

# Result: win.result["data"] is the reordered list.
```
