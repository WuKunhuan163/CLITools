# Tkinter GUI Layer

Tkinter-based GUI components for the AITerminalTools ecosystem: blueprints, widgets, and shared styling.

## Structure

- `blueprint/`: Reusable window templates (account_login, bottom_bar, button_bar, etc.)
- `widget/`: Custom widgets (UndoableText)
- `style.py`: Shared fonts, colors, and config loading

## Key Exports

- `style.py`: `get_label_style`, `get_secondary_label_style`, `get_button_style`, `get_status_style`, `get_gui_colors`, `get_gui_config`
- `blueprint/base.py`: `BaseGUIWindow`, `setup_common_bottom_bar`, `filter_tkinter_noise`
- `blueprint/timed_bottom_bar/gui.py`: Re-export of BaseGUIWindow, setup_common_bottom_bar

## Dependencies

- `logic.lang.utils.get_translation` for localization
- `logic.utils.find_project_root` for paths
- `logic.gui.engine` for sandbox detection and bell playback
