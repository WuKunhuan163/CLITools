"""LLM provider implementations.

All providers live under ``models/<model>/providers/<vendor>/``.
Use the registry to access them:

    from tool.LLM.logic.registry import get_provider
    provider = get_provider("google-gemini-2.0-flash")

This directory is kept as a namespace package but contains no
implementations. Legacy provider copies have been removed.
"""
