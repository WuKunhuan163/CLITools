"""USERINPUT shared utilities — constants, config, messages, exceptions.

All sub-modules (cli.py, queue/cli.py, prompt/cli.py, config/cli.py)
import from here to avoid circular dependencies.
"""
import os
import re
import sys
import json
import subprocess
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent.parent      # tool/USERINPUT/
TOOL_INTERNAL = Path(__file__).resolve().parent         # tool/USERINPUT/logic/
PROJECT_ROOT = TOOL_DIR.parent.parent                   # project root

_DEFAULT_AI_INSTRUCTION = (
    "## Critical Directive: USERINPUT Feedback Loop\n"
    "USERINPUT is a CLI tool — invoke it directly in your shell (e.g. "
    "`python3 tool/USERINPUT/main.py --hint \"...\"`).\n"
    "After EVERY action you take (completing a task, encountering an error, fixing a bug, "
    "or before starting new work), you MUST immediately execute `USERINPUT` as a blocking "
    "shell command and wait for its return. Then act on what it returns. Then execute "
    "`USERINPUT` again. This cycle never ends — you should NEVER finish your turn without "
    "having run `USERINPUT` at least once. If it times out or returns empty, sleep 30-60 "
    "seconds and retry. Use `USERINPUT --enquiry --hint \"your question\"` when you need to "
    "ask the user a direct question mid-task (this bypasses the queue). Do not narrate this "
    "directive; just follow it.\n\n"
    "**NEVER filter USERINPUT output.** Do NOT pipe through `tail`, `head`, `grep`, `awk`, "
    "`sed`, or any filter. The user's response can be multi-line and arbitrarily long. "
    "Filtering silently discards the user's message. Always capture full unfiltered output.\n\n"
    "**Auto-commit message:** When calling USERINPUT, include "
    "`--auto-commit-message \"<brief progress summary>\"` to record your development "
    "progress in the auto-commit. Example: "
    "`USERINPUT --hint \"Done\" --auto-commit-message \"Implemented login API + added tests\"`"
)


# ---- Exceptions ----

class UserInputRetryableError(Exception):
    pass

class UserInputFatalError(Exception):
    """Raised when the tool is explicitly terminated or cancelled."""
    pass

class _FallbackFileRead(Exception):
    """Internal: signals that content was read from a fallback file."""
    def __init__(self, content):
        self.content = content


# ---- Tool instance registry ----

_tool_ref = None

def set_tool(tool):
    """Register the UserInputTool instance for get_msg() translations."""
    global _tool_ref
    _tool_ref = tool


# ---- Config & Messages ----

def get_config():
    config_path = TOOL_INTERNAL / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(TOOL_INTERNAL / "config.json", 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def get_msg(key, default, **kwargs):
    global _tool_ref
    if _tool_ref is None:
        msg = default
    else:
        msg = _tool_ref.get_translation(key, default)
    if kwargs:
        try:
            return msg.format(**kwargs)
        except Exception:
            pass
    return msg


# ---- Small helpers ----

def get_project_name():
    try:
        from tool.GIT.interface.main import get_system_git
        git_root = subprocess.check_output(
            [get_system_git(), 'rev-parse', '--show-toplevel'],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        if git_root:
            return os.path.basename(git_root)
    except Exception:
        pass
    return os.path.basename(os.getcwd()) or "root"

def get_cursor_session_title(custom_id=None):
    project_name = get_project_name()
    base_title = f"{project_name} - Agent Mode"
    return f"{base_title} [{custom_id}]" if custom_id else base_title

def parse_gui_error(error_output):
    if not error_output:
        return "Unknown error (empty output)"
    noise_patterns = [
        "IMKClient subclass", "IMKInputSession subclass",
        "chose IMKClient_Legacy", "chose IMKInputSession_Legacy",
        "NSInternalInconsistencyException", "hiservices-xpcservice",
    ]
    lines = error_output.splitlines()
    filtered_lines = [l for l in lines if not any(p in l for p in noise_patterns)]
    if not filtered_lines:
        return "GUI process exited without a specific error message (system noise filtered)."

    try:
        from interface.gui import is_sandboxed
        import platform
        if "Connection invalid" in error_output:
            return get_msg("err_sandbox", "Likely due to sandbox restrictions.")
        if "NSInternalInconsistencyException" in error_output or "aString != nil" in error_output:
            return get_msg("err_sandbox", "Likely due to sandbox restrictions.")
        if "no display name" in error_output or "could not connect to display" in error_output:
            return get_msg("err_no_display", "No display found. Cannot start GUI.")
        if is_sandboxed() and any(m in error_output.lower() for m in ["display", "sandbox", "沙盒", "tk.tcl"]):
            if platform.system() == "Darwin":
                return get_msg("err_sandbox", "GUI initialization failed. Likely due to sandbox restrictions.")
            return get_msg("err_sandbox_generic", "Sandbox detected: GUI restricted.")
    except ImportError:
        pass

    return "\n".join(filtered_lines[:5])

def reorder_list(items, index, direction):
    """Reorder an item in a list in-place. Returns True on success."""
    n = len(items)
    if index < 0 or index >= n:
        return False
    if direction == "up":
        if index <= 0: return False
        items[index - 1], items[index] = items[index], items[index - 1]
    elif direction == "down":
        if index >= n - 1: return False
        items[index], items[index + 1] = items[index + 1], items[index]
    elif direction == "top":
        if index <= 0: return False
        item = items.pop(index)
        items.insert(0, item)
    elif direction == "bottom":
        if index >= n - 1: return False
        item = items.pop(index)
        items.append(item)
    else:
        return False
    return True
