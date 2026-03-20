# Editable List Blueprint - Agent Guide

## Dependency Chain

```
BaseGUIWindow (base.py)
    -> BottomBarWindow (bottom_bar/gui.py)
        -> EditableListWindow (editable_list/gui.py)
```

## Quick Usage

```python
from logic._.gui.tkinter.blueprint.editable_list.gui import EditableListWindow

win = EditableListWindow(
    title="My List Manager",
    internal_dir=str(logic_dir),
    tool_name="MY_TOOL",
    items=["Item A", "Item B", "Item C"],
    list_label="Items:",
    allow_add=True,
    allow_edit=True,
    allow_delete=True,
)
win.run()
# win.result["status"] == "success" -> win.result["data"] is the final list
```

## External Control Commands

For programmatic testing without GUI interaction:

```python
win.cmd_select(0)          # Select first item
win.cmd_move_down()        # Move selected down
win.cmd_move_to_top()      # Move selected to top
win.cmd_add("New item")    # Add item
win.cmd_edit(0, "Updated") # Edit item at index
win.cmd_delete(1)          # Delete item at index
items = win.cmd_get_items() # Get current list
win.cmd_save()             # Trigger save
win.cmd_cancel()           # Trigger cancel
```

## Result Format (Interface I)

```json
{"status": "success", "data": ["Item B", "Item A", "New item"]}
```

On cancel: `{"status": "cancelled", "data": [...]}`
