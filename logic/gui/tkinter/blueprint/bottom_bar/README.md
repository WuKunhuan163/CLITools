# GUI Blueprint: bottom_bar

A minimal GUI window with Cancel and Save action buttons at the bottom. This is a simpler alternative to `timed_bottom_bar` for use cases that do not require a countdown timer, "Add Time" button, or periodic focus/bell behavior.

## Architecture

- **Base Class**: `BottomBarWindow` (inherits `BaseGUIWindow`)
- **Utility**: `setup_bottom_bar(parent, window_instance, save_text, save_cmd, cancel_text, cancel_cmd)`

## Components

- **Status Label**: Left-aligned text for transient status messages.
- **Cancel Button**: Finalizes with `"cancelled"` status.
- **Save Button**: Primary action button. Finalizes with `"success"` status.

## Dependency

```
BaseGUIWindow (base.py) -> BottomBarWindow (bottom_bar/gui.py)
```

## Usage

```python
from logic.gui.tkinter.blueprint.bottom_bar.gui import BottomBarWindow

class MyWindow(BottomBarWindow):
    def __init__(self):
        super().__init__("My Window", internal_dir=str(logic_dir), tool_name="MY_TOOL")

    def get_current_state(self):
        return self.my_data

    def setup_content(self, parent_frame):
        # Build your UI here
        ...

win = MyWindow()
win.run()
```

## Blueprints that inherit from bottom_bar

- `editable_list` - Reorderable list manager with this bottom bar.
