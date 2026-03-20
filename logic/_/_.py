"""EcoCommand — alias for CliEndpoint, the base class for all cli.py endpoints.

Canonical location: __/interface/cli.py
This module re-exports CliEndpoint as EcoCommand for existing eco command files.
"""
# TODO: Remove EcoCommand alias — use CliEndpoint from interface.base directly
from __.interface.cli import CliEndpoint

EcoCommand = CliEndpoint

__all__ = ["EcoCommand", "CliEndpoint"]
