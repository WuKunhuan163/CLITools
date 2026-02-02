from tool.GIT.logic.engine import GitEngine
import os

def get_git_engine():
    """Returns a GitEngine instance for the current project."""
    # Find project root
    from pathlib import Path
    curr = Path(__file__).resolve()
    while curr.parent != curr:
        if (curr / "tool.json").exists():
            return GitEngine(str(curr))
        curr = curr.parent
    return GitEngine(os.getcwd())

