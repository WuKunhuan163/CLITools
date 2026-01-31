#!/usr/bin/env python3
import sys
from pathlib import Path

def get_background_manager():
    """Returns the background process manager."""
    from tool.BACKGROUND.logic.manager import BackgroundManager
    return BackgroundManager()

def run_background_cmd_func():
    """Returns a function to run a command in the background."""
    from tool.BACKGROUND.logic.manager import BackgroundManager
    def run_bg(command, name=None):
        manager = BackgroundManager()
        return manager.start_process(command, name=name)
    return run_bg

