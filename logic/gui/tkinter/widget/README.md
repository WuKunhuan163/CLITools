# Tkinter Widget Blueprints

Standardized reusable widgets for the `TOOL` ecosystem.

## Widgets

### `UndoableText` (`text.py`)
A `tk.Text` replacement with built-in undo/redo support and platform-aware shortcuts (Ctrl+Z / Cmd+Z).

#### Usage
```python
from logic.gui.tkinter.widget.text import UndoableText

# Using the factory method
text_widget = UndoableText.create(master, width=40, height=10)
```

