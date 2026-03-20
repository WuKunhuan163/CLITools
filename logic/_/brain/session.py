"""Backward compatibility shim — session management moved to logic._.brain.instance.session."""
from logic._.brain.instance.session import BrainSessionManager  # noqa: F401

__all__ = ["BrainSessionManager"]
