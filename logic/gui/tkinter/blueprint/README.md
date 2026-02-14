# Tkinter GUI Blueprints

This directory contains standardized Tkinter GUI blueprints used across the AITerminalTools ecosystem.

## Structure

- `base.py`: Contains shared logic for all blueprints, including system noise filtering.
- `timed_bottom_bar/`: A blueprint featuring a status label, countdown timer, and action buttons.
- `account_login/`: A blueprint for account and password entry.
- `two_factor_auth/`: A blueprint for n-digit 2FA code entry.

## Design Principles

1. **Process Isolation**: All GUIs run in their own subprocess to avoid blocking the main terminal.
2. **State Management**: GUIs capture "State A" and return it as JSON to the parent process via "Interface I".
3. **Consistent Styling**: Use `logic/gui/tkinter/style.py` for a unified look and feel.
4. **Resiliency**: Built-in timeout and signal handling.

