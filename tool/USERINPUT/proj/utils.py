import os
import sys
from pathlib import Path

def get_python_not_found_hint(tool_name, version, script_dir, _func):
    """
    Returns a list of strings representing the localized hint for missing Python dependency.
    """
    setup_path = script_dir / "setup.py"
    v_clean = version.replace('python', '')
    
    hints = [
        _func("err_python_not_found", "Python tool '{version}' not found, cannot launch GUI.").format(version=version),
        _func("err_python_not_found_hint_1", "The tool '{tool_name}' depends on the PYTHON tool.").format(tool_name=tool_name),
        _func("err_python_not_found_hint_2", "Please run: TOOL install PYTHON"),
        _func("err_python_not_found_hint_3", "Then run: PYTHON --py-install {version}").format(version=v_clean),
        _func("err_python_not_found_hint_4", "Finally, run the tool's setup: {tool_name} setup").format(tool_name=tool_name)
    ]
    return hints

def print_python_not_found_error(tool_name, version, script_dir, _func):
    """
    Prints the localized error and hints for missing Python dependency.
    """
    hints = get_python_not_found_hint(tool_name, version, script_dir, _func)
    error_label = _func("label_error", "Error")
    
    print(f"\033[1;31m{error_label}\033[0m: {hints[0]}", flush=True)
    for hint in hints[1:]:
        print(hint, flush=True)

