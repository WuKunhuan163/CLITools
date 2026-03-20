"""SHIM — CliEndpoint has moved to __/interface/cli.py.

This file re-exports for backward compatibility during migration.
All new code should import from interface.base or __.interface.cli.
"""
# TODO: Remove this shim after all imports are migrated to interface.base
from __.interface.cli import CliEndpoint  # noqa: F401
