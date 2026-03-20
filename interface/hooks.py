"""Hooks engine interface.

Provides HookInstance and HookInterface for tool hook implementations.
"""
# TODO: [migration] This facade will be migrated/rewritten as part of the __/ architecture restructure.
from logic._.hooks.engine import HookInstance, HookInterface, HooksEngine

__all__ = [
    "HookInstance",
    "HookInterface",
    "HooksEngine",
]
