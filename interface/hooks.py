"""Hooks engine interface.

Provides HookInstance and HookInterface for tool hook implementations.
"""
from logic.hooks.engine import HookInstance, HookInterface, HooksEngine

__all__ = [
    "HookInstance",
    "HookInterface",
    "HooksEngine",
]
