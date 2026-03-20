# Tkinter Widget Package - Agent Guide

## Overview

Custom Tkinter widgets used across GUI blueprints. Currently contains `UndoableText`.

## UndoableText (text.py)

A `tk.Text` replacement with built-in undo/redo and platform-aware shortcuts.

### Factory Method

```python
from logic._.gui.tkinter.widget.text import UndoableText

text_widget = UndoableText.create(master, width=40, height=10, **kwargs)
```

### Key Behavior

- Enables `undo=True`, `autoseparators=True`, `maxundo=-1` by default
- **macOS**: Cmd+Z (undo), Cmd+Shift+Z / Cmd+Y (redo)
- **Windows/Linux**: Ctrl+Z (undo), Ctrl+Y / Ctrl+Shift+Z (redo)
- `_undo` / `_redo` catch `tk.TclError` and return `"break"` to avoid propagation

### Usage Pattern

Use when you need a multi-line text input with undo/redo. Pass through standard `tk.Text` kwargs (e.g., `wrap`, `height`, `font`).
