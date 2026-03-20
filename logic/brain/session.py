"""Backward compatibility shim — session management moved to logic.brain.instance.session."""
from logic.brain.instance.session import BrainSessionManager  # noqa: F401

__all__ = ["BrainSessionManager"]
