"""LLM provider registry.

Central point for discovering, configuring, and instantiating LLM providers.
"""
from typing import Dict, Any, List

from tool.LLM.logic.base import LLMProvider


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


_ALIASES = {
    "nvidia_glm47": "nvidia-glm-4-7b",
    "zhipu_glm4": "zhipu-glm-4-flash",
}


def get_provider(name: str = "nvidia-glm-4-7b", **kwargs) -> LLMProvider:
    """Get a provider instance by name.

    Raises:
        ValueError: If the provider name is not registered.
    """
    _ensure_builtins()
    resolved = _ALIASES.get(name, name)
    if resolved not in _REGISTRY:
        available = ", ".join(_REGISTRY.keys())
        raise ValueError(
            f"Unknown LLM provider '{name}'. Available: {available}")
    return _REGISTRY[resolved](**kwargs)


def get_default_provider(**kwargs) -> LLMProvider:
    """Get the default provider."""
    return get_provider("nvidia-glm-4-7b", **kwargs)


_builtins_loaded = False


def _ensure_builtins():
    """Lazy-load built-in providers."""
    global _builtins_loaded
    if _builtins_loaded:
        return
    _builtins_loaded = True

    from tool.LLM.logic.providers.nvidia_glm47 import NvidiaGLM47Provider
    register("nvidia-glm-4-7b", NvidiaGLM47Provider)

    from tool.LLM.logic.providers.zhipu_glm4 import ZhipuGLM4Provider
    register("zhipu-glm-4-flash", ZhipuGLM4Provider)
