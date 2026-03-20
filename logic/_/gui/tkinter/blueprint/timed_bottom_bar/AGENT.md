# Timed Bottom Bar Blueprint - Agent Guide

## Core Concepts

`timed_bottom_bar` is a re-export layer. The actual implementation lives in `base.py`:
- `BaseGUIWindow`: Base class with timer, signals, remote control.
- `setup_common_bottom_bar`: Creates status label, Submit, Add Time, Cancel buttons.

## Import Path

```python
from logic._.gui.tkinter.blueprint.base import BaseGUIWindow, setup_common_bottom_bar
```

## BaseGUIWindow Key Methods

| Method | Description |
|--------|-------------|
| `get_current_state()` | Override: return State A for finalize |
| `finalize(status, data, reason)` | Unified closure; prints GDS_GUI_RESULT_JSON |
| `start_timer(status_label)` | Countdown; calls finalize on timeout |
| `trigger_add_time(increment, status_label)` | Add time, pulse UI, notify parent |
| `run(setup_func, on_show, custom_id)` | Main entry: setup, mainloop, cleanup |

## setup_common_bottom_bar Parameters

- `parent`: Root or frame
- `window_instance`: BaseGUIWindow instance
- `submit_text`: Primary button label
- `submit_cmd`: Callback for primary button
- `add_time_increment`: Seconds to add (0 = no Add Time button)

Returns: `status_label` for timer/status display.

## Remote Control (data/run/stops/)

Flag files: `{pid}.stop`, `{pid}.submit`, `{pid}.cancel`, `{pid}.add_time`. Created by `handle_gui_remote_command` in manager.py. GUI polls via `check_signals()` every 500ms.

## Gotchas

- All logic is in `base.py`. Import directly from `logic._.gui.tkinter.blueprint.base`.
- Blueprints that need timer + Add Time inherit from `BaseGUIWindow` and call `setup_common_bottom_bar`.
