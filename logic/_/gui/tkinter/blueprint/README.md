# Tkinter GUI Blueprints

This directory contains standardized Tkinter GUI blueprints used across the AITerminalTools ecosystem.

## Structure

- `base.py`: Contains shared logic for all blueprints, including system noise filtering.
- `timed_bottom_bar/`: A blueprint featuring a status label, countdown timer, and action buttons.
- `bottom_bar/`: A minimal blueprint with Cancel/Save buttons (no timer).
- `editable_list/`: A reorderable list manager inheriting from `bottom_bar`.
- `button_bar/`: A horizontal button row blueprint.
- `account_login/`: A blueprint for account and password entry.
- `two_step_login/`: A two-step login blueprint (account then password).
- `two_factor_auth/`: A blueprint for n-digit 2FA code entry.
- `tutorial/`: A multi-step wizard blueprint.

## Inheritance Hierarchy

```
BaseGUIWindow (base.py)
+-- timed_bottom_bar (status, countdown, Add Time, Cancel, Submit)
|   +-- account_login
|   +-- two_step_login
|   +-- two_factor_auth
|   +-- tutorial
+-- bottom_bar (status, Cancel, Save)
|   +-- editable_list (reorderable list + Cancel/Save)
+-- button_bar (horizontal button row)
```

## Design Principles

1. **Process Isolation**: All GUIs run in their own subprocess to avoid blocking the main terminal.
2. **State Management**: GUIs capture "State A" and return it as JSON to the parent process via "Interface I".
3. **Consistent Styling**: Use `logic/_/gui/tkinter/style.py` for a unified look and feel.
4. **Resiliency**: Built-in timeout and signal handling.

