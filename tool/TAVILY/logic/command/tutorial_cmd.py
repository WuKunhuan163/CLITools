#!/usr/bin/env python3
"""TAVILY --setup-tutorial command: run the interactive setup wizard."""
import sys
import importlib.util
from pathlib import Path
from logic.config import get_color

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent)

def _(key, default, **kwargs):
    from logic.lang.utils import get_translation
    return get_translation(_LOGIC_DIR, key, default, **kwargs)


def _make_step_callback():
    """Create a callback that prints Turing Machine-style step progress to terminal."""
    BOLD = get_color("BOLD")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    def on_step_change(step_idx, total_steps, step_title):
        msg = f"{BOLD}{BLUE}{_('turing_user_completing', 'User completing')} {step_idx + 1}/{total_steps}{RESET}: {step_title}..."
        sys.stdout.write(f"\r\033[K{msg}")
        sys.stdout.flush()

    return on_step_change


def execute(tool, **kwargs):
    tutorial_path = Path(__file__).resolve().parent.parent / "tutorial" / "setup_guide" / "main.py"
    spec = importlib.util.spec_from_file_location("tavily_tutorial", str(tutorial_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    res = module.run_setup_tutorial(on_step_change=_make_step_callback())
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()
    if res.get("status") == "success":
        success_label = _("label_successfully_completed", "Successfully completed")
        tutorial_name = _("success_setup_tutorial", "TAVILY setup tutorial.")
        print(f"{get_color('BOLD')}{get_color('GREEN')}{success_label}{get_color('RESET')} {tutorial_name}")
        return 0
    else:
        reason = res.get('reason') or res.get('status') or 'Unknown'
        print(f"{get_color('BOLD')}{get_color('RED')}{_('tutorial_exited', 'Tutorial exited')}{get_color('RESET')}: {reason}")
        return 1
