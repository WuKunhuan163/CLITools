# GUI Blueprint Development Guide for Agents

This directory contains reusable Tkinter GUI blueprints designed for seamless integration with AI-driven terminal tools. Every blueprint follows a standardized architectural pattern called **Interface I**, ensuring process isolation, reliable state capture, and consistent styling.

## Core Principles

1. **Process Isolation**: All GUIs run in a separate subprocess. This prevents Tkinter's event loop from blocking the main tool logic and allows for robust output suppression (e.g., macOS IMK noise).
2. **Interface I (Standard Output)**: Upon completion, the GUI script MUST print a single line starting with `GDS_GUI_RESULT_JSON:` followed by a JSON object containing the `status` and `data`.
3. **State Recovery (State A)**: The `data` field in the result JSON should represent the final state of the UI (e.g., entered credentials, selected options) at the time of closure.
4. **Resiliency**: GUIs must handle timeouts and external signals (SIGINT/SIGTERM) gracefully, ensuring the current state is saved before exit.

## Available Blueprints

### 1. Base Window (`base.py`)
The foundation for all blueprints. Provides:
- Integrated countdown timer and "Add Time" logic.
- Automated signal handling.
- MacOS system noise suppression.
- `callback_queue` for thread-safe UI updates from background threads.

### 2. Account Login (`account_login`)
A standardized login interface with:
- Pre-fillable account field.
- Password visibility toggle (👁 icon).
- Built-in verification loop (5 attempts by default) using a background thread to keep the UI responsive.
- Detailed history logging of failed attempts.

### 3. Two-Factor Auth (`two_factor_auth`)
A boxy numeric code entry interface:
- Supports N digits (default 6).
- Auto-focusing next/previous boxes on input/backspace.
- Loading state with "Verifying..." status.

## How to use in your Tool

### Minimal Calling Code
Use the `run_gui` method provided by `ToolBase`:

```python
from logic.tool.blueprint.base import ToolBase

tool = ToolBase("MyTool")
# ...
res = tool.run_gui(sys.executable, "/path/to/gui_script.py", timeout=300)

if res["status"] == "success":
    data = res["data"]
    # ... process data ...
```

### Reference Implementation
Refer to the `demo.py` file in each blueprint directory. These files demonstrate a dual-mode script that acts as both the parent (manager) and the child (actual GUI):

1. **Parent Mode**: Uses `ProgressTuringMachine` to show a "Waiting for feedback..." status in the terminal.
2. **Child Mode**: (Detected via `GDS_GUI_MANAGED` env var) Actually launches the Tkinter window.

## Styling Guidelines
- **Status Styles**: Use `logic.gui.tkinter.style` helpers (`get_label_style`, `get_gui_colors`, etc.) to maintain visual consistency.
- **Button Feedback**: When processing, the primary button should change to `Verifying ...` or `Logging In ...` and other buttons should be hidden.
- **Error Feedback**: Use `error_label` (usually red, italic) below input fields for in-window error messages.
