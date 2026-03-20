import sys
from typing import Any

# Lazy import for tkinter
tk = None

def _get_tk():
    global tk
    if tk is None:
        import tkinter as _tk
        tk = _tk
    return tk

class UndoableText:
    """
    Mixin-like helper to create a Tkinter Text widget with undo/redo support.
    Can be used via factory function or inheritance.
    """
    @staticmethod
    def create(master, **kwargs) -> Any:
        import tkinter as tk
        # Enable built-in undo/redo
        kwargs.setdefault('undo', True)
        kwargs.setdefault('autoseparators', True)
        kwargs.setdefault('maxundo', -1)
        
        text_widget = tk.Text(master, **kwargs)
        
        # Determine platform for shortcuts
        is_macos = False
        try:
            if master.tk.call('tk', 'windowingsystem') == 'aqua':
                is_macos = True
        except:
            if sys.platform == 'darwin':
                is_macos = True

        if is_macos:
            text_widget.bind('<Command-z>', lambda e: UndoableText._undo(text_widget))
            text_widget.bind('<Command-Shift-Z>', lambda e: UndoableText._redo(text_widget))
            text_widget.bind('<Command-y>', lambda e: UndoableText._redo(text_widget))
        else:
            text_widget.bind('<Control-z>', lambda e: UndoableText._undo(text_widget))
            text_widget.bind('<Control-y>', lambda e: UndoableText._redo(text_widget))
            text_widget.bind('<Control-Shift-Z>', lambda e: UndoableText._redo(text_widget))
            
        return text_widget

    @staticmethod
    def _undo(widget):
        import tkinter as tk
        try:
            widget.edit_undo()
        except tk.TclError:
            pass
        return "break"

    @staticmethod
    def _redo(widget):
        import tkinter as tk
        try:
            widget.edit_redo()
        except tk.TclError:
            pass
        return "break"

