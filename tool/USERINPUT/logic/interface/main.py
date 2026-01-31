#!/usr/bin/env python3
import sys
from pathlib import Path

def get_user_input_func():
    """Returns the function to capture user input via Tkinter GUI."""
    from tool.USERINPUT.main import get_user_input_tkinter
    return get_user_input_tkinter

def get_user_input_tool_class():
    """Returns the UserInputTool class."""
    from tool.USERINPUT.main import UserInputTool
    return UserInputTool

