"""Accessibility interface.

Provides keyboard accessibility monitoring and permission requests.
"""
# TODO: [migration] This facade will be migrated/rewritten as part of the __/ architecture restructure.
from logic._.utils.accessibility.keyboard.monitor import (
    check_accessibility_trusted,
    request_accessibility_permission,
)

__all__ = [
    "check_accessibility_trusted",
    "request_accessibility_permission",
]
