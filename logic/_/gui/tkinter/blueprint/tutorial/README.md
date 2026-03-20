# GUI Blueprint: tutorial

Multi-step wizard interface for setup guides, onboarding, or sequential user input.

## Purpose

Display steps one at a time with Prev/Next navigation, optional validation per step, and scrollable content area.

## Structure

- `gui.py`: `TutorialWindow`, `TutorialStep` classes
- `demo.py`: Demo with two steps (welcome + code validation)

## Key Features

- **Step Indicator**: "Step a/b" in top-left
- **Content Container**: Scrollable frame cleared and rebuilt per step
- **Validation**: `validate_func` can disable Next until conditions are met
- **Buttons**: Prev, Next/Complete, Cancel, Add Time (inherited from timed_bottom_bar)

## Usage

```python
from logic._.gui.tkinter.blueprint.tutorial.gui import TutorialWindow, TutorialStep

def build_step_1(frame, win):
    tk.Label(frame, text="Welcome").pack()

def build_step_2(frame, win):
    # Add inputs, store refs on win
    pass

def validate_step_2():
    return win.demo_code == "123456"

steps = [
    TutorialStep("Welcome", build_step_1),
    TutorialStep("Verify", build_step_2, validate_func=validate_step_2),
]
win = TutorialWindow(
    title="Setup Wizard",
    timeout=600,
    internal_dir=str(logic_dir),
    steps=steps
)
win.run(win.setup_ui)
```

## TutorialStep

- `title`: Step name
- `content_func(frame, window)`: Builds UI in frame; receives window for shared state
- `validate_func()`: Optional; return True to enable Next
