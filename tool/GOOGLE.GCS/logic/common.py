#!/usr/bin/env python3 -u
"""Backward-compatibility shim: all functionality moved to utils.py."""
from pathlib import Path as _Path
import importlib.util as _ilu

_utils_path = _Path(__file__).resolve().parent / "utils.py"
_spec = _ilu.spec_from_file_location("gcs_logic_utils", str(_utils_path))
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

for _name in dir(_mod):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_mod, _name)
