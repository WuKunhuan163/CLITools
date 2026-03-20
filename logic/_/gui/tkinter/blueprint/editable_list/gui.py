"""
Editable List Blueprint - A reorderable list manager with Cancel/Save bottom bar.

Dependency chain:
    BaseGUIWindow (base.py)
        -> BottomBarWindow (bottom_bar/gui.py)
            -> EditableListWindow (this file)

Features:
    - Displays a numbered list of text items.
    - Move Up / Move Down / Move to Top / Move to Bottom buttons.
    - Add / Edit / Delete items.
    - Drag-and-drop reordering (optional).
    - Cancel / Save bottom bar inherited from BottomBarWindow.
    - External control commands via class methods for programmatic testing.

External control interface (for testing and automation):
    - EditableListWindow.cmd_select(index)       Select item by 0-based index.
    - EditableListWindow.cmd_move_up()            Move selected item up.
    - EditableListWindow.cmd_move_down()          Move selected item down.
    - EditableListWindow.cmd_move_to_top()        Move selected item to top.
    - EditableListWindow.cmd_move_to_bottom()     Move selected item to bottom.
    - EditableListWindow.cmd_add(text)            Append a new item.
    - EditableListWindow.cmd_edit(index, text)    Replace item at index.
    - EditableListWindow.cmd_delete(index)        Remove item at index.
    - EditableListWindow.cmd_get_items()          Return current list of items.
    - EditableListWindow.cmd_save()               Trigger save action.
    - EditableListWindow.cmd_cancel()             Trigger cancel action.
"""
import sys
from pathlib import Path
from typing import Optional, Callable, List

_script_path = Path(__file__).resolve()
_project_root = _script_path.parent.parent.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from logic._.gui.tkinter.blueprint.bottom_bar.gui import BottomBarWindow
from logic._.gui.tkinter.style import get_label_style, get_button_style


class EditableListWindow(BottomBarWindow):
    """
    A GUI window that displays a reorderable list of text items
    with a Cancel/Save bottom bar.

    Constructor args:
        title:           Window title.
        internal_dir:    Directory for localization.
        tool_name:       Tool identifier.
        items:           Initial list of string items.
        allow_add:       Show an "Add" button (default True).
        allow_edit:      Show an "Edit" button (default True).
        allow_delete:    Show an "Delete" button (default True).
        save_text:       Label for the primary button (default "Save").
        cancel_text:     Label for the cancel button (default "Cancel").
        window_size:     Tkinter geometry string.
        list_label:      Optional header text above the list.
    """
    def __init__(self, title: str, internal_dir: str, tool_name: str = None,
                 items: List[str] = None,
                 allow_add: bool = True,
                 allow_edit: bool = True,
                 allow_delete: bool = True,
                 save_text: str = "Save",
                 cancel_text: str = "Cancel",
                 window_size: str = "600x450",
                 list_label: str = None):
        super().__init__(title, internal_dir=internal_dir, tool_name=tool_name,
                         save_text=save_text, cancel_text=cancel_text,
                         window_size=window_size)
        self._items = list(items) if items else []
        self.allow_add = allow_add
        self.allow_edit = allow_edit
        self.allow_delete = allow_delete
        self.list_label_text = list_label
        self.listbox = None
        self._sidebar_buttons = {}

    # ── State ──────────────────────────────────────────────

    def get_current_state(self) -> List[str]:
        return list(self._items)

    # ── Content setup (called by BottomBarWindow.setup_ui) ─

    def setup_content(self, parent_frame):
        import tkinter as tk

        if self.list_label_text:
            tk.Label(parent_frame, text=self.list_label_text,
                     font=get_label_style(), anchor="w").pack(fill=tk.X, pady=(0, 5))

        body = tk.Frame(parent_frame)
        body.pack(fill=tk.BOTH, expand=True)

        # Listbox + scrollbar
        list_frame = tk.Frame(body)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(
            list_frame, font=get_label_style(), selectmode=tk.SINGLE,
            yscrollcommand=scrollbar.set, activestyle="dotbox"
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        self._refresh_listbox()

        # Sidebar buttons
        sidebar = tk.Frame(body)
        sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        btn_font = get_button_style()
        btn_w = 12

        def _add_btn(name, text, command):
            b = tk.Button(sidebar, text=text, command=command, font=btn_font, width=btn_w)
            b.pack(pady=2, fill=tk.X)
            self._sidebar_buttons[name] = b
            return b

        _add_btn("move_top", "Move to Top", self.cmd_move_to_top)
        _add_btn("move_up", "Move Up", self.cmd_move_up)
        _add_btn("move_down", "Move Down", self.cmd_move_down)
        _add_btn("move_bottom", "Move to Bottom", self.cmd_move_to_bottom)

        if self.allow_add:
            tk.Frame(sidebar, height=10).pack()
            _add_btn("add", "Add", self._on_add_click)
        if self.allow_edit:
            _add_btn("edit", "Edit", self._on_edit_click)
        if self.allow_delete:
            _add_btn("delete", "Delete", self._on_delete_click)

    # ── Listbox helpers ────────────────────────────────────

    def _refresh_listbox(self):
        if not self.listbox:
            return
        self.listbox.delete(0, "end")
        for i, item in enumerate(self._items):
            self.listbox.insert("end", f"{i}: {item}")

    def _selected_index(self) -> Optional[int]:
        sel = self.listbox.curselection()
        if sel:
            return sel[0]
        return None

    def _select_and_see(self, idx: int):
        if 0 <= idx < len(self._items):
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(idx)
            self.listbox.see(idx)
            self.listbox.activate(idx)

    # ── Button click handlers (with dialog) ────────────────

    def _on_add_click(self):
        self._show_input_dialog("Add Item", "", self._do_add)

    def _on_edit_click(self):
        idx = self._selected_index()
        if idx is None:
            return
        self._show_input_dialog("Edit Item", self._items[idx],
                                lambda text: self._do_edit(idx, text))

    def _on_delete_click(self):
        idx = self._selected_index()
        if idx is None:
            return
        self.cmd_delete(idx)

    def _do_add(self, text):
        if text and text.strip():
            self.cmd_add(text.strip())

    def _do_edit(self, idx, text):
        if text and text.strip():
            self.cmd_edit(idx, text.strip())

    def _show_input_dialog(self, title: str, initial: str, callback: Callable):
        import tkinter as tk

        line_count = max(3, min(15, initial.count("\n") + 1))
        char_width = 60
        longest_line = max((len(l) for l in initial.split("\n")), default=0) if initial else 0
        if longest_line > char_width:
            line_count = max(line_count, min(15, line_count + longest_line // char_width))
        dlg_height = 80 + line_count * 22

        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.geometry(f"550x{dlg_height}")
        dlg.minsize(400, 160)
        dlg.transient(self.root)
        dlg.grab_set()

        frame = tk.Frame(dlg, padx=15, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        text_frame = tk.Frame(frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(
            text_frame, font=get_label_style(), wrap=tk.WORD,
            height=line_count, yscrollcommand=scrollbar.set
        )
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)

        if initial:
            text_widget.insert("1.0", initial)
            text_widget.tag_add("sel", "1.0", "end")
        text_widget.focus_set()

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X)

        def on_ok():
            callback(text_widget.get("1.0", tk.END).strip())
            dlg.destroy()

        tk.Button(btn_frame, text="OK", command=on_ok,
                  font=get_button_style(primary=True)).pack(side=tk.RIGHT)
        tk.Button(btn_frame, text="Cancel", command=dlg.destroy,
                  font=get_button_style()).pack(side=tk.RIGHT, padx=(0, 10))

        text_widget.bind("<Escape>", lambda e: dlg.destroy())

    # ── External control commands ──────────────────────────

    def cmd_select(self, index: int):
        """Select item at 0-based index."""
        self._select_and_see(index)

    def cmd_move_up(self):
        """Move the selected item up by one position."""
        idx = self._selected_index()
        if idx is None or idx <= 0:
            return
        self._items[idx - 1], self._items[idx] = self._items[idx], self._items[idx - 1]
        self._refresh_listbox()
        self._select_and_see(idx - 1)

    def cmd_move_down(self):
        """Move the selected item down by one position."""
        idx = self._selected_index()
        if idx is None or idx >= len(self._items) - 1:
            return
        self._items[idx], self._items[idx + 1] = self._items[idx + 1], self._items[idx]
        self._refresh_listbox()
        self._select_and_see(idx + 1)

    def cmd_move_to_top(self):
        """Move the selected item to the top of the list."""
        idx = self._selected_index()
        if idx is None or idx == 0:
            return
        item = self._items.pop(idx)
        self._items.insert(0, item)
        self._refresh_listbox()
        self._select_and_see(0)

    def cmd_move_to_bottom(self):
        """Move the selected item to the bottom of the list."""
        idx = self._selected_index()
        if idx is None or idx == len(self._items) - 1:
            return
        item = self._items.pop(idx)
        self._items.append(item)
        self._refresh_listbox()
        self._select_and_see(len(self._items) - 1)

    def cmd_add(self, text: str):
        """Append a new item to the list."""
        self._items.append(text)
        self._refresh_listbox()
        self._select_and_see(len(self._items) - 1)

    def cmd_edit(self, index: int, text: str):
        """Replace the item at the given index."""
        if 0 <= index < len(self._items):
            self._items[index] = text
            self._refresh_listbox()
            self._select_and_see(index)

    def cmd_delete(self, index: int):
        """Remove the item at the given index."""
        if 0 <= index < len(self._items):
            self._items.pop(index)
            self._refresh_listbox()
            if self._items:
                self._select_and_see(min(index, len(self._items) - 1))

    def cmd_get_items(self) -> List[str]:
        """Return the current list of items."""
        return list(self._items)

    def cmd_save(self):
        """Programmatically trigger the save action."""
        self.on_save()

    def cmd_cancel(self):
        """Programmatically trigger the cancel action."""
        self.finalize("cancelled", self.get_current_state())
