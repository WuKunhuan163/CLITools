"""test_00_help — Verify GS --help flag works."""

import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BIN = _PROJECT_ROOT / "bin" / "GS" / "GS"


def test_help_flag():
    r = subprocess.run([sys.executable, str(_PROJECT_ROOT / "tool" / "GOOGLE.GS" / "main.py"), "--help"],
                       capture_output=True, text=True, timeout=30,
                       env={"PYTHONPATH": str(_PROJECT_ROOT)})
    assert r.returncode == 0, f"--help returned {r.returncode}: {r.stderr}"
    assert "Google Scholar" in r.stdout, f"Missing description in help: {r.stdout[:200]}"


if __name__ == "__main__":
    test_help_flag()
    print("PASS: test_00_help")
