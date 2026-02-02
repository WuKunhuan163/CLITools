#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

def test_git_proxy():
    """Test if GIT tool correctly forwards commands to system git."""
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    git_bin = project_root / "bin" / "GIT"
    
    if not git_bin.exists():
        print(f"Error: GIT binary not found at {git_bin}")
        return False

    # Test 'git status'
    result = subprocess.run([str(git_bin), "status", "--porcelain"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: 'GIT status' failed with code {result.returncode}")
        print(f"Stderr: {result.stderr}")
        return False
    
    print("Success: 'GIT status' correctly forwarded to system git.")
    
    # Test 'git rev-parse --abbrev-ref HEAD'
    result = subprocess.run([str(git_bin), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: 'GIT rev-parse' failed with code {result.returncode}")
        return False
    
    print(f"Success: 'GIT rev-parse' returned current branch: {result.stdout.strip()}")
    return True

if __name__ == "__main__":
    if test_git_proxy():
        print("\nOverall Status: PASS")
        sys.exit(0)
    else:
        print("\nOverall Status: FAIL")
        sys.exit(1)

