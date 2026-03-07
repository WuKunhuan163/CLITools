#!/usr/bin/env python3
import sys
from pathlib import Path

def get_python_install_dir():
    """Returns the directory where Python versions are installed."""
    from tool.PYTHON.logic.config import INSTALL_DIR
    return INSTALL_DIR

def get_python_exe_func():
    """Returns a function that finds a Python executable for a given version."""
    from tool.PYTHON.logic.utils import get_python_exec
    return get_python_exec

