#!/usr/bin/env python3
"""
BACKGROUND Tool Interface

Provides functions for other tools to manage background processes
without CLI overhead.
"""

def get_background_manager():
    """Returns an instantiated BackgroundManager for process management.
    
    Usage:
        mgr = get_background_manager()
        pid = mgr.run_cmd(["python3", "long_task.py"])
        mgr.list_procs()
        mgr.stop_proc(pid)
    """
    from tool.BACKGROUND.main import BackgroundManager
    return BackgroundManager()


def run_in_background(cmd_list):
    """Convenience: run a command in the background and return its PID."""
    mgr = get_background_manager()
    return mgr.run_cmd(cmd_list)
