# GUI Blueprint: button_bar

A horizontal row of buttons with optional instruction text. Inherits from `BaseGUIWindow` and supports timed interaction, countdown-disable buttons, and accessibility-aware unlock behavior.

## Purpose

Display a set of action buttons for quick user selection (e.g., "Allow", "Deny", "Retry"). Supports optional instruction text with bold formatting (`**text**`), per-button styling, and delayed unlock for security-sensitive choices.

## Structure

- `gui.py`: `ButtonBarWindow` class and setup logic.

## Key Features

- **Instruction Area**: Optional multi-line text above buttons with `**bold**` support.
- **Per-Button Config**: Each button can specify `text`, `cmd`, `bg`, `fg`, `font`, `close_on_click`, `return_value`, `disable_seconds`.
- **Countdown Unlock**: Buttons with `disable_seconds` start disabled and unlock after countdown or when user regains focus / presses Cmd/Ctrl.
- **CDP Mode**: `disable_auto_unlock=True` skips keyboard/focus auto-unlock for CDP-driven flows.
- **Status Updates**: `update_status_line(new_status)` for dynamic instruction updates.

## Usage

```python
from logic.gui.tkinter.blueprint.button_bar.gui import ButtonBarWindow

win = ButtonBarWindow(
    title="Confirm Action",
    timeout=60,
    internal_dir=str(logic_dir),
    buttons=[
        {"text": "Allow", "close_on_click": True, "return_value": "allow"},
        {"text": "Deny", "close_on_click": True, "return_value": "deny", "disable_seconds": 5},
    ],
    instruction_text="Choose an option:"
)
win.run()
```
