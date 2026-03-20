"""Hook instance: persistence_locker

Automatically saves untracked tool data when leaving dev branch
and restores it when entering dev branch.
"""
from pathlib import Path


def on_checkout(source_branch: str, target_branch: str, project_root: str):
    """Save locker when leaving dev, restore when entering dev."""
    from logic._.git.persistence import get_persistence_manager

    root = Path(project_root)
    pm = get_persistence_manager(root)

    if source_branch == "dev" and target_branch != "dev":
        key = pm.save_tools_data(branch="dev")
        if key:
            from interface.config import get_color
            BOLD = get_color("BOLD")
            RESET = get_color("RESET")
            print(f"  {BOLD}Locker saved{RESET} (dev branch data).")

    if target_branch == "dev":
        key = pm.find_locker_for_branch("dev")
        if key:
            pm.restore(key)
            from interface.config import get_color
            BOLD = get_color("BOLD")
            GREEN = get_color("GREEN")
            RESET = get_color("RESET")
            print(f"  {BOLD}{GREEN}Locker restored{RESET} (dev branch data).")
