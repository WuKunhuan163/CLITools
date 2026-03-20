# GUI Blueprint: account_login

This blueprint provides a specialized interface for collecting user credentials (Account and Password). It inherits the core timed behavior and styling from the `timed_bottom_bar` blueprint.

## Key Features
- **Two-Field Input**: Standard Account/Email field and a masked Password field.
- **Customizable Labels**: All text fields (Instruction, Account Label, Password Label) can be overridden via constructor arguments.
- **Validation Support**: Built-in check for empty fields with status bar error reporting.
- **Standard Interactions**: Supports `Enter` key submission and inherits all timer/remote control features.

## Usage
Import `AccountLoginWindow` and instantiate it with your tool's translation directory.

```python
from logic._.gui.tkinter.blueprint.account_login.gui import AccountLoginWindow

win = AccountLoginWindow(
    title="My Login",
    timeout=300,
    internal_dir="/path/to/my/tool/logic",
    instruction_text="Login to My Tool"
)
win.run(win.setup_ui)
```

