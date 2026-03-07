# GUI Blueprint: two_step_login

Two-step login flow: account entry first, then password if needed. Supports session reuse (skip password) and full authentication.

## Purpose

Handle login flows where the server may return "session reused" (no password needed) or "need password" (proceed to password step). Common for Apple ID and similar services.

## Structure

- `gui.py`: `TwoStepLoginWindow` class
- `demo.py`: Demo with mock verify_handler

## Key Features

- **Step 1 (Account)**: User enters account. Handler returns `success`, `need_password`, or `error`.
- **Step 2 (Password)**: Account locked; user enters password. Handler returns `success` or `error`.
- **Prev Button**: Return from password step to account step.
- **Attempt Counting**: Only password-step failures count toward max_attempts (default 5).

## Usage

```python
from logic.gui.tkinter.blueprint.two_step_login.gui import TwoStepLoginWindow

def verify_handler(state):
    if state["step"] == "account":
        if is_session_reusable(state["account"]):
            return {"status": "success", "data": {...}}
        return {"status": "need_password"}
    else:
        if authenticate(state["account"], state["password"]):
            return {"status": "success", "data": {...}}
        return {"status": "error", "message": "Invalid password"}

win = TwoStepLoginWindow(
    title="Sign In",
    timeout=300,
    internal_dir=str(logic_dir),
    verify_handler=verify_handler
)
win.run(win.setup_ui)
```
