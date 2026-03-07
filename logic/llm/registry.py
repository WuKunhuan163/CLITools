"""LLM provider registry.

Central point for discovering, configuring, and instantiating LLM providers.
Any tool in the project can call ``get_provider()`` to obtain a ready-to-use
LLM backend.

Usage:
    from logic.llm.registry import get_provider, list_providers

    provider = get_provider("nvidia_glm47")
    result = provider.send([{"role": "user", "content": "Hi"}])
"""
from typing import Dict, Any, List, Optional

from logic.llm.base import LLMProvider


_REGISTRY: Dict[str, type] = {}


def register(name: str, cls: type):
    """Register a provider class."""
    _REGISTRY[name] = cls


def list_providers() -> List[Dict[str, Any]]:
    """Return info dicts for all registered providers."""
    _ensure_builtins()
    results = []
    for name, cls in _REGISTRY.items():
        try:
            instance = cls()
            results.append(instance.get_info())
        except Exception as e:
            results.append({"name": name, "available": False, "error": str(e)})
    return results


def get_provider(name: str = "nvidia_glm47", **kwargs) -> LLMProvider:
    """Get a provider instance by name.

    Args:
        name: Provider identifier (default: nvidia_glm47).
        **kwargs: Passed to the provider constructor.

    Raises:
        ValueError: If the provider name is not registered.
    """
    _ensure_builtins()
    if name not in _REGISTRY:
        available = ", ".join(_REGISTRY.keys())
        raise ValueError(
            f"Unknown LLM provider '{name}'. Available: {available}")
    return _REGISTRY[name](**kwargs)


def get_default_provider(**kwargs) -> LLMProvider:
    """Get the default provider (nvidia_glm47)."""
    return get_provider("nvidia_glm47", **kwargs)


_builtins_loaded = False


def _ensure_builtins():
    """Lazy-load built-in providers."""
    global _builtins_loaded
    if _builtins_loaded:
        return
    _builtins_loaded = True

    from logic.llm.nvidia_glm47 import NvidiaGLM47Provider
    register("nvidia_glm47", NvidiaGLM47Provider)
