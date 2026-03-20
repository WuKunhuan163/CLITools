import sys
from pathlib import Path

# Base directories
PROJ_DIR = Path(__file__).resolve().parent
PYTHON_TOOL_DIR = PROJ_DIR.parent
DATA_DIR = PYTHON_TOOL_DIR / "data"
INSTALL_DIR = DATA_DIR / "install"
AUDIT_DIR = DATA_DIR / "audit"

# Project root (AITerminalTools)
PROJECT_ROOT = PYTHON_TOOL_DIR.parent.parent

# Resource directory in 'tool' branch
RESOURCE_ROOT = PROJECT_ROOT / "logic" / "_" / "install" / "resource" / "PYTHON" / "data" / "install"

# Temporary download/install directory
TMP_INSTALL_DIR = DATA_DIR / "tmp" / "install"

# Worker settings
DEFAULT_CONCURRENCY = 3

# Ensure necessary directories exist
def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_INSTALL_DIR.mkdir(parents=True, exist_ok=True)

def get_rel_install_path():
    """Returns the relative path string for checking if an executable is managed."""
    return "data/install/"

def get_install_path(version_tag):
    """Returns the path to a specific python installation."""
    return INSTALL_DIR / version_tag / "install"

def get_executable_path(version_tag):
    """Returns the path to the python executable for a specific version."""
    install_path = get_install_path(version_tag)
    if sys.platform == "win32":
        return install_path / "python.exe"
    else:
        # Check both bin/python3 and bin/python (some builds might differ)
        py3 = install_path / "bin" / "python3"
        if py3.exists():
            return py3
        return install_path / "bin" / "python"

