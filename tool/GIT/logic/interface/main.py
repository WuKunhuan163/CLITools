from tool.GIT.logic.engine import GitEngine
from pathlib import Path
import sys
import subprocess
import json

def get_git_engine():
    # Robust project root detection for the interface
    from logic.utils import find_project_root
    project_root = find_project_root(Path(__file__))
    return GitEngine(project_root)

def run_git(args, cwd=None):
    """
    Interface function to run git commands.
    By default captures output and suppresses terminal printing.
    """
    engine = get_git_engine()
    # Use the engine's run_git which already captures output
    return engine.run_git(args, cwd=cwd)

def run_git_with_status(args, cwd=None):
    """
    Runs git and returns (success, stdout, stderr).
    """
    res = run_git(args, cwd=cwd)
    return res.returncode == 0, res.stdout, res.stderr

def run_git_tool_managed(args, cwd=None):
    """
    Runs the GIT tool itself with managed output.
    This is what the user referred to as '托管执行'.
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
