# Two-Factor Authentication (2FA) Blueprint

Standardized Tkinter UI for capturing N-digit verification codes.

## Features
- **Square digit boxes**: Apple-style separate entry boxes for each digit.
- **Auto-focus**: Automatically moves to the next box after entering a digit.
- **Backspace handling**: Correctly handles backspacing to previous boxes.
- **Input validation**: Restricts input to allowed characters (default: 0-9).
- **Auto-submit**: Optional auto-submission once all digits are entered.

## Usage
```python
from logic._.gui.tkinter.blueprint.two_factor_auth.gui import TwoFactorAuthWindow

win = TwoFactorAuthWindow(
    title="Verification",
    timeout=300,
    internal_dir=tool_internal_dir,
    n=6 # Number of digits
)
win.run(win.setup_ui)
print(win.result)
```

