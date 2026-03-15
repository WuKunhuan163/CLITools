"""LLM provider registry.

Central point for discovering, configuring, and instantiating LLM providers.
Each provider has: interface (API client) + pipeline (context/tool handling).
"""
from typing import Dict, Any, List, Optional

from tool.LLM.logic.base import LLMProvider
from tool.LLM.logic.pipeline import ContextPipeline


_REGISTRY: Dict[str, type] = {}
_PIPELINES: Dict[str, ContextPipeline] = {}


def register(name: str, cls: type, pipeline: Optional[ContextPipeline] = None):
    """Register a provider class and its optional pipeline."""
    _REGISTRY[name] = cls
    if pipeline:
        _PIPELINES[name] = pipeline


def get_pipeline(name: str) -> ContextPipeline:
    """Get the context pipeline for a provider. Falls back to base."""
    _ensure_builtins()
    resolved = _ALIASES.get(name, name)
    return _PIPELINES.get(resolved, ContextPipeline())


def list_providers() -> List[Dict[str, Any]]:
    """Return info dicts for all registered providers."""
    _ensure_builtins()
    results = []
    for name, cls in _REGISTRY.items():
        try:
            instance = cls()
            info = instance.get_info()
            info["has_pipeline"] = name in _PIPELINES
            results.append(info)
        except Exception as e:
            results.append({"name": name, "available": False, "error": str(e)})
    return results


_ALIASES = {
    "nvidia_glm47": "nvidia-glm-4-7b",
    "zhipu_glm4": "zhipu-glm-4-flash",
    "zhipu_glm47": "zhipu-glm-4.7",
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

    from tool.LLM.logic.providers.nvidia_glm47.interface import NvidiaGLM47Provider
    from tool.LLM.logic.providers.nvidia_glm47.pipeline import NvidiaContextPipeline
    register("nvidia-glm-4-7b", NvidiaGLM47Provider, NvidiaContextPipeline())

    from tool.LLM.logic.providers.zhipu_glm4.interface import ZhipuGLM4Provider
    from tool.LLM.logic.providers.zhipu_glm4.pipeline import ZhipuContextPipeline
    register("zhipu-glm-4-flash", ZhipuGLM4Provider, ZhipuContextPipeline())

    from tool.LLM.logic.providers.zhipu_glm47.interface import ZhipuGLM47Provider
    from tool.LLM.logic.providers.zhipu_glm47.pipeline import ZhipuGLM47Pipeline
    register("zhipu-glm-4.7", ZhipuGLM47Provider, ZhipuGLM47Pipeline())
