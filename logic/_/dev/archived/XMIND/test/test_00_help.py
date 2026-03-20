"""Test XMIND --help exits cleanly."""
import subprocess
import sys
from pathlib import Path

_PROJ = Path(__file__).resolve().parent.parent.parent.parent
_BIN = _PROJ / "bin" / "XMIND" / "XMIND"


def test_help_exits_0():
    r = subprocess.run([sys.executable, str(_BIN), "--help"],
                       capture_output=True, text=True, timeout=10)
    assert r.returncode == 0
    assert "XMIND" in r.stdout or "xmind" in r.stdout.lower()


if __name__ == "__main__":
    test_help_exits_0()
    print("PASS: test_00_help")
