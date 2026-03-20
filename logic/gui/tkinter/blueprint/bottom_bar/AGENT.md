# Bottom Bar Blueprint - Agent Guide

## Core Concepts

`BottomBarWindow` provides a minimal Cancel/Save bottom bar without timer or Add Time. Use when you need persistent action buttons but not timed interaction.

## Inheritance

```
BaseGUIWindow (base.py) -> BottomBarWindow (bottom_bar/gui.py)
```

## Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `title` | str | Window title |
| `internal_dir` | str | Localization directory |
| `tool_name` | str | Tool identifier |
| `save_text` | str | Primary button label (default "Save") |
| `cancel_text` | str | Cancel button label (default "Cancel") |
| `window_size` | str | Tkinter geometry (default "500x400") |

## Override Points

- `get_current_state()`: Return data to pass back on save. Must override.
- `setup_content(parent_frame)`: Build main UI content. Must override.

## Utility: setup_bottom_bar

```python
setup_bottom_bar(parent, window_instance, save_text, save_cmd, cancel_text, cancel_cmd) -> status_label
```

Creates the bottom bar frame. If `save_cmd`/`cancel_cmd` are None, defaults to `finalize("success", ...)` and `finalize("cancelled", ...)`.

## Usage Pattern

```python
class MyWindow(BottomBarWindow):
    def get_current_state(self):
        return self.my_data

    def setup_content(self, parent_frame):
        # Build UI in parent_frame
        pass

win = MyWindow("Title", internal_dir=logic_dir)
win.run()  # Uses setup_ui internally
```

## Result Format (Interface I)

- Save: `{"status": "success", "data": get_current_state()}`
- Cancel: `{"status": "cancelled", "data": get_current_state()}`
