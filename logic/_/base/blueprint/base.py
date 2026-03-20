"""SHIM — ToolBase has moved to __/interface/base.py.

This file re-exports for backward compatibility during migration.
All new code should import from interface.base or __.interface.base.
"""
# TODO: Remove this shim after all imports are migrated to interface.base
from __.interface.base import ToolBase  # noqa: F401
