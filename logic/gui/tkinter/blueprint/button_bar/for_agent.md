# Button Bar Blueprint - Agent Guide

## Core Concepts

`ButtonBarWindow` displays a horizontal row of buttons. Each button can close the window and return a value. Buttons with `disable_seconds` start disabled and unlock via countdown, focus regain, or Cmd/Ctrl key.

## Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `title` | str | Window title |
| `timeout` | int | Auto-close seconds |
| `internal_dir` | str | Localization directory |
| `buttons` | List[Dict] | Button configs (see below) |
| `instruction` | str | Optional text above buttons |
| `window_size` | str | Tkinter geometry (default "500x120") |
| `on_startup` | Callable | Callback after UI setup |
| `focus_interval` | int | Seconds between focus/bell (default 45) |
| `disable_auto_unlock` | bool | If True, skip keyboard/focus unlock (CDP mode) |

## Button Config Dict Keys

- `text`: Button label
- `cmd`: Optional callback on click
- `close_on_click`: If True, finalize with `return_value` on click
- `return_value`: Value for `data` when closed via this button (default: `text`)
- `bg`, `fg`, `font`, `relief`, `bd`: Optional styling
- `disable_seconds`: Seconds before button becomes clickable
- `on_click`: Optional callback receiving button widget reference

## Result Format (Interface I)

On button click with `close_on_click`: `{"status": "success", "data": return_value}`

## Gotchas

- **macOS subprocess**: Global keyboard capture (pynput) is unreliable in subprocesses; Cmd key detection via tkinter is used as fallback.
- **disable_seconds**: Unlock triggers: countdown expiry, FocusIn after FocusOut, Cmd/Ctrl key, or paste+Enter (when pynput available).
- **update_status_line**: Replaces the last line of instruction text; used for CDP status updates.
