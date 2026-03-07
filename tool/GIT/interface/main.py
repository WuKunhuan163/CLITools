from tool.GIT.logic.engine import GitEngine
from pathlib import Path
import os
import sys
import shutil
import subprocess
import json

_GIT_BINARY_CACHE = None


def get_system_git() -> str:
    """Resolve the real system ``git`` binary, bypassing any PATH shadows.

    On macOS, ``bin/GIT/`` in PATH can shadow ``/usr/bin/git`` due to
    case-insensitive APFS.  This function searches PATH with our project
    ``bin/`` directories excluded, falling back to well-known locations.

    Returns
    -------
    str
        Absolute path to the system git binary.
    """
    global _GIT_BINARY_CACHE
    if _GIT_BINARY_CACHE:
        return _GIT_BINARY_CACHE

    # Build a clean PATH excluding our project's bin/ directories
    project_markers = ("AITerminalTools", "bin/GIT", "bin/GITHUB", "bin/GITLAB")
    clean_dirs = []
    for p in os.environ.get("PATH", "").split(os.pathsep):
        if not any(m in p for m in project_markers):
            clean_dirs.append(p)
    clean_path = os.pathsep.join(clean_dirs)

    found = shutil.which("git", path=clean_path)
    if found:
        _GIT_BINARY_CACHE = found
        return found

    # Fallback to well-known locations
    for candidate in ("/usr/bin/git", "/usr/local/bin/git", "/opt/homebrew/bin/git"):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            _GIT_BINARY_CACHE = candidate
            return candidate

    _GIT_BINARY_CACHE = "git"
    return "git"


def get_git_engine():
    """Return a ``GitEngine`` bound to the project root."""
    from logic.utils import find_project_root
    project_root = find_project_root(Path(__file__))
    return GitEngine(project_root)


def run_git(args, cwd=None):
    """Run a git command via the engine (captures output, no terminal print).

    Parameters
    ----------
    args : list[str]
        Git sub-command and arguments, e.g. ``["status", "--porcelain"]``.
    cwd : str or None
        Working directory override.

    Returns
    -------
    subprocess.CompletedProcess
    """
    engine = get_git_engine()
    return engine.run_git(args, cwd=cwd)

def run_git_with_status(args, cwd=None):
    """Run a git command and return a ``(success, stdout, stderr)`` tuple.

    Parameters
    ----------
    args : list[str]
        Git sub-command and arguments.
    cwd : str or None
        Working directory override.

    Returns
    -------
    tuple[bool, str, str]
        ``(success, stdout, stderr)``
    """
    res = run_git(args, cwd=cwd)
    return res.returncode == 0, res.stdout, res.stderr


def run_git_tool_managed(args, cwd=None):
    """Run git through the GIT tool binary with managed output capture.

    Uses the installed ``bin/GIT/GIT`` executable, falling back to the
    tool source.  Parses ``TOOL_RESULT_JSON`` from stdout when present.

    Parameters
    ----------
    args : list[str]
        Git sub-command and arguments.
    cwd : str or None
        Working directory override.

    Returns
    -------
    subprocess.CompletedProcess or namedtuple
    """
    # Find the GIT tool executable
    project_root = get_git_engine().project_root
    if not project_root:
        return run_git(args, cwd=cwd)
    
    bin_path = project_root / "bin" / "GIT" / "GIT"
    if not bin_path.exists():
        bin_path = project_root / "bin" / "GIT"
    if not bin_path.exists():
        bin_path = project_root / "tool" / "GIT" / "main.py"
    
    cmd = [sys.executable, str(bin_path)] + args + ["--tool-quiet"]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    
    # Parse the TOOL_RESULT_JSON if present
    for line in res.stdout.splitlines():
        if line.startswith("TOOL_RESULT_JSON:"):
            data = json.loads(line[len("TOOL_RESULT_JSON:"):])
            # Return a mock CompletedProcess-like object
            from collections import namedtuple
            Result = namedtuple("Result", ["returncode", "stdout", "stderr"])
            return Result(data["returncode"], data["stdout"], data["stderr"])
            
    return res
