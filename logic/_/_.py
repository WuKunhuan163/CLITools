"""EcoCommand — alias for CliEndpoint, the base class for all cli.py endpoints.

Canonical location: logic/base/cli.py
This module re-exports CliEndpoint as EcoCommand for existing eco command files.
"""
from logic.base.cli import CliEndpoint

EcoCommand = CliEndpoint

__all__ = ["EcoCommand", "CliEndpoint"]
