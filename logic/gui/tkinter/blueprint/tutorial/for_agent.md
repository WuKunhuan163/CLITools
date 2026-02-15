# GUI Blueprint: Tutorial

## Overview
The `TutorialWindow` blueprint provides a standardized multi-step "Wizard" interface. It is ideal for setup guides, step-by-step instructions, or any process that requires sequential user input.

## Components
- **Step Indicator**: Automatically displays "Step a/b" in the top-left.
- **Content Container**: A central `tk.Frame` that is cleared and rebuilt for each step.
- **Navigation Bar**: Includes standard `Previous`, `Next` (or `Complete`), `Cancel`, and `Add Time` buttons.
- **Conditional Progression**: Each step can have a `validate_func` to prevent the user from proceeding until certain conditions are met.

## Usage

### 1. Define Steps
Each step is defined by a `TutorialStep` object:
```python
step = TutorialStep(
    title="My Step",
    content_func=my_builder_func,
    validate_func=my_validator_func
)
```
- `content_func(frame, window)`: Receives the container frame and the window instance.
- `validate_func()`: Should return `True` to allow progression.

### 2. Initialize and Run
```python
win = TutorialWindow(
    title="My Tutorial",
    timeout=300,
    internal_dir=str(Path(__file__).parent),
    steps=[step1, step2, ...]
)
win.run(win.setup_ui)
```

## Demo
See `demo.py` for a complete working example with:
1. A basic informational step.
2. A verification step requiring a specific 6-digit code.

## Key Methods
- `show_error(msg, is_info=False)`: Displays a message in the bottom status area of the window.
- `update_step_ui()`: Manually triggers a refresh of the current step (rarely needed).
- `get_current_state()`: Returns `{"current_step": index, "total_steps": count}`.

