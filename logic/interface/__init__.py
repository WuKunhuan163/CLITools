"""Compatibility shim — re-exports from the new root interface/ package.

The interface layer has moved from logic/interface/ to interface/.
This module exists solely for backward compatibility.
"""
from interface import get_interface, list_interfaces

__all__ = ["get_interface", "list_interfaces"]
