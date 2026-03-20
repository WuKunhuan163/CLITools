"""Redirect: tutorial_cmd moved to logic/tutorial/src/tutorial_cmd.py"""
import importlib.util
from pathlib import Path

_CANONICAL = Path(__file__).resolve().parent.parent / "tutorial" / "src" / "tutorial_cmd.py"

def execute(tool, **kwargs):
    spec = importlib.util.spec_from_file_location("gds_tutorial_cmd", str(_CANONICAL))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.execute(tool, **kwargs)
