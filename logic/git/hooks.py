"""Git hooks integration -- install/manage real .git/hooks/ scripts.

Provides installation of a ``post-checkout`` hook that triggers the
persistence locker automatically when using raw ``git checkout``.
"""
import os
import stat
from pathlib import Path


_POST_CHECKOUT_SCRIPT = '''\
#!/bin/sh
# AITerminalTools post-checkout hook -- persistence locker
# Installed by: TOOL --dev install-hooks

PREV_HEAD="$1"
NEW_HEAD="$2"
BRANCH_FLAG="$3"

# Only run on branch checkouts (flag=1), not file checkouts (flag=0)
[ "$BRANCH_FLAG" = "0" ] && exit 0

ROOT="$(git rev-parse --show-toplevel)"
PREV_BRANCH="$(git name-rev --name-only "$PREV_HEAD" 2>/dev/null | sed 's|remotes/origin/||')"
NEW_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

# Skip if both are the same
[ "$PREV_BRANCH" = "$NEW_BRANCH" ] && exit 0

# Invoke the Python hook
python3 -c "
import sys; sys.path.insert(0, '$ROOT')
from tool.GIT.hooks.instance.persistence_locker import on_checkout
on_checkout('$PREV_BRANCH', '$NEW_BRANCH', '$ROOT')
" 2>/dev/null

exit 0
'''


def install_hooks(project_root: Path) -> bool:
    """Install the ``post-checkout`` hook into ``.git/hooks/``."""
    hooks_dir = project_root / ".git" / "hooks"
    if not hooks_dir.exists():
        return False

    target = hooks_dir / "post-checkout"

    # Don't overwrite user-created hooks
    if target.exists():
        content = target.read_text()
        if "AITerminalTools" not in content:
            return False

    target.write_text(_POST_CHECKOUT_SCRIPT)
    target.chmod(target.stat().st_mode | stat.S_IEXEC)
    return True


def uninstall_hooks(project_root: Path) -> bool:
    """Remove the AITerminalTools ``post-checkout`` hook."""
    target = project_root / ".git" / "hooks" / "post-checkout"
    if not target.exists():
        return False

    content = target.read_text()
    if "AITerminalTools" in content:
        target.unlink()
        return True
    return False


def is_hook_installed(project_root: Path) -> bool:
    """Check if our post-checkout hook is installed."""
    target = project_root / ".git" / "hooks" / "post-checkout"
    if not target.exists():
        return False
    return "AITerminalTools" in target.read_text()
