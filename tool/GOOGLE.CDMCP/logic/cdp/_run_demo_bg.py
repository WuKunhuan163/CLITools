"""Auto-generated demo runner. Paths resolved dynamically."""
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_tool_dir = _here.parent.parent
_project_root = _tool_dir.parent.parent

sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_tool_dir))

from logic.resolve import setup_paths
setup_paths(__file__)

import importlib.util
spec = importlib.util.spec_from_file_location('demo', str(_here / 'demo.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
