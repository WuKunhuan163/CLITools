# GUI Blueprint: timed_bottom_bar

This blueprint provides a standardized Tkinter window template designed for timed user interactions. It is the default "Look & Feel" for tools in the `AITerminalTools` ecosystem.

## Key Features
- **Countdown Timer**: Automatically manages a remaining time display and triggers a timeout state when it reaches zero.
- **Unified Bottom Bar**: Includes a status label, "Add Time" button (programmable increment), and "Cancel"/"Submit" buttons.
- **Signal Handling**: Gracefully handles `SIGINT` and `SIGTERM`, capturing the current state before exit.
- **Remote Control**: Supports remote signals via file-based flags in `data/run/stops/`. CLI flags: `--gui-submit`, `--gui-cancel`, `--gui-stop`, `--gui-add-time` (with optional `--id <id>`).
- **Periodic Focus**: Can be configured to periodically steal focus and play a notification bell to ensure user awareness.

## Architecture
- **Base Class**: `BaseGUIWindow`
- **Utility**: `setup_common_bottom_bar`

## Components
- **Status Label**: Displays current status or remaining time.
- **Action Buttons**: Primary action (e.g., Login, Submit) and lifecycle actions (Cancel, Add Time).

## Usage
Tools should inherit from `BaseGUIWindow` and call `setup_common_bottom_bar` during their `setup_ui` phase.

