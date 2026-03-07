"""Re-export from tool.LLM — the canonical LLM provider registry.

Usage:
    from logic.llm.registry import get_provider, list_providers
"""
from tool.LLM.logic.registry import (  # noqa: F401
    register,
    list_providers,
    get_provider,
    get_default_provider,
)
