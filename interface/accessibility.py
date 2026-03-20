"""Accessibility interface.

Provides keyboard accessibility monitoring and permission requests.
"""
from logic.accessibility.keyboard.monitor import (
    check_accessibility_trusted,
    request_accessibility_permission,
)

__all__ = [
    "check_accessibility_trusted",
    "request_accessibility_permission",
]
