# GUI Blueprint Development Guide for Agents

When creating or modifying GUI blueprints, follow these technical standards.

## Blueprint Inheritance

- All window blueprints should inherit from `BaseGUIWindow` (currently in `timed_bottom_bar/gui.py`, but refactor to `base.py` is recommended for future).
- Implement `get_current_state()` to return the data the user has entered.
- Call `self.finalize("success", data)` when the user completes the action.

## Shared Interface (Interface I)

- Communication between the GUI subprocess and the Tool manager is done via `GDS_GUI_RESULT_JSON:{...}` printed to `stdout`.
- The `manager.py` handles parsing this JSON and filtering out system noise.

## Output Suppression

- **macOS Noise**: Tkinter on macOS often prints `IMKClient` logs. Use `filter_tkinter_noise` from `logic.gui.tkinter.blueprint.base` in the manager, or FD-level redirection in the window's `run()` method.
- **Sensitive Data**: Never print the raw result JSON unless `GDS_GUI_MANAGED` is set to "1" in the environment.

## Logic点击 (Button Feedback)

- When an action button (like Login) is clicked, it should provide immediate visual feedback.
- Preferred style: Disable the button and change its text to `···` while processing.

## Retry Logic

- For authentication tools, implement at least 5 retries by default.
- Pass the attempt count and total count to the GUI to display in error labels: `Error Message (a/b)`.

