"""LLM provider registry.

Central point for discovering, configuring, and instantiating LLM providers.
Structure: models/<model>/providers/<vendor>/ with model.json at model level.

Registry names follow the pattern: <vendor>-<model> (e.g. "zhipu-glm-4-flash").
Model-level resolution: "glm-4-flash" resolves to the preferred provider.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from tool.LLM.logic.base import LLMProvider
from tool.LLM.logic.pipeline import ContextPipeline


_REGISTRY: Dict[str, type] = {}
_PIPELINES: Dict[str, ContextPipeline] = {}
_MODEL_PROVIDERS: Dict[str, List[str]] = {}

_MODELS_DIR = Path(__file__).parent / "models"


def register(name: str, cls: type, pipeline: Optional[ContextPipeline] = None,
             model: str = ""):
    """Register a provider class and its optional pipeline."""
    _REGISTRY[name] = cls
    if pipeline:
        _PIPELINES[name] = pipeline
    if model:
        _MODEL_PROVIDERS.setdefault(model, []).append(name)


def get_pipeline(name: str) -> ContextPipeline:
    """Get the context pipeline for a provider. Falls back to base."""
    _ensure_builtins()
    resolved = _resolve(name)
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


def list_models() -> List[Dict[str, Any]]:
    """Return info for each model with its available providers."""
    _ensure_builtins()
    results = []
    for model, providers in _MODEL_PROVIDERS.items():
        model_json_path = _MODELS_DIR / model.replace("-", "_").replace(".", "_") / "model.json"
        meta = {}
        if model_json_path.exists():
            try:
                meta = json.loads(model_json_path.read_text())
            except Exception:
                pass
        results.append({
            "model": model,
            "display_name": meta.get("display_name", model),
            "providers": providers,
            "capabilities": meta.get("capabilities", {}),
            "cost": meta.get("cost", {}),
        })
    return results


_ALIASES = {
    "nvidia_glm47": "nvidia-glm-4-7b",
    "nvidia-glm-4.7b": "nvidia-glm-4-7b",
    "zhipu_glm4": "zhipu-glm-4-flash",
    "zhipu_glm47": "zhipu-glm-4.7",
    "zhipu_glm47_flash": "zhipu-glm-4.7-flash",
    "glm-4-flash": "zhipu-glm-4-flash",
    "glm-4.7": "zhipu-glm-4.7",
    "glm-4.7-flash": "zhipu-glm-4.7-flash",
    "gemini-2.0-flash": "google-gemini-2.0-flash",
    "gemini-2.0": "google-gemini-2.0-flash",
    "gemini-flash": "google-gemini-2.0-flash",
    "ernie-speed-8k": "baidu-ernie-speed-8k",
    "ernie-speed": "baidu-ernie-speed-8k",
    "ernie-3.5-8k": "baidu-ernie-speed-8k",
    "ernie-speed-pro-128k": "baidu-ernie-speed-8k",
    "ernie-speed-pro": "baidu-ernie-speed-8k",
    "hunyuan-lite": "tencent-hunyuan-lite",
    "qwen2.5-7b": "siliconflow-qwen2.5-7b",
    "qwen-2.5-7b": "siliconflow-qwen2.5-7b",
    "siliconflow-qwen": "siliconflow-qwen2.5-7b",
    "auto": "auto",
}


def _resolve(name: str) -> str:
    """Resolve aliases and model names to provider names."""
    resolved = _ALIASES.get(name, name)
    if resolved in _REGISTRY:
        return resolved
    if resolved in _MODEL_PROVIDERS:
        for prov in _MODEL_PROVIDERS[resolved]:
            if prov in _REGISTRY:
                try:
                    inst = _REGISTRY[prov]()
                    if inst.is_available():
                        return prov
                except Exception:
                    continue
        return _MODEL_PROVIDERS[resolved][0] if _MODEL_PROVIDERS[resolved] else resolved
    return resolved


def get_provider(name: str = "zhipu-glm-4-flash", **kwargs) -> LLMProvider:
    """Get a provider instance by name or model name.

    Raises:
        ValueError: If the provider name is not registered.
    """
    _ensure_builtins()
    resolved = _resolve(name)
    if resolved not in _REGISTRY:
        available = ", ".join(_REGISTRY.keys())
        raise ValueError(
            f"Unknown LLM provider '{name}'. Available: {available}")
    return _REGISTRY[resolved](**kwargs)


def get_default_provider(**kwargs) -> LLMProvider:
    """Get the default provider."""
    return get_provider("zhipu-glm-4-flash", **kwargs)


_builtins_loaded = False


def _ensure_builtins():
    """Lazy-load built-in providers from models/ directory."""
    global _builtins_loaded
    if _builtins_loaded:
        return
    _builtins_loaded = True

    from tool.LLM.logic.models.glm_4_flash.providers.zhipu.interface import ZhipuGLM4Provider
    from tool.LLM.logic.models.glm_4_flash.providers.zhipu.pipeline.context import ZhipuContextPipeline
    register("zhipu-glm-4-flash", ZhipuGLM4Provider, ZhipuContextPipeline(), model="glm-4-flash")

    from tool.LLM.logic.models.glm_4_7.providers.nvidia.interface import NvidiaGLM47Provider
    from tool.LLM.logic.models.glm_4_7.providers.nvidia.pipeline import NvidiaContextPipeline
    register("nvidia-glm-4-7b", NvidiaGLM47Provider, NvidiaContextPipeline(), model="glm-4.7")

    from tool.LLM.logic.models.glm_4_7.providers.zhipu.interface import ZhipuGLM47Provider
    from tool.LLM.logic.models.glm_4_7.providers.zhipu.pipeline import ZhipuGLM47Pipeline
    register("zhipu-glm-4.7", ZhipuGLM47Provider, ZhipuGLM47Pipeline(), model="glm-4.7")

    from tool.LLM.logic.models.glm_4_7_flash.providers.zhipu.interface import ZhipuGLM47FlashProvider
    from tool.LLM.logic.models.glm_4_7_flash.providers.zhipu.pipeline import ZhipuGLM47FlashPipeline
    register("zhipu-glm-4.7-flash", ZhipuGLM47FlashProvider, ZhipuGLM47FlashPipeline(), model="glm-4.7-flash")

    from tool.LLM.logic.models.gemini_2_0_flash.providers.google.interface import GoogleGeminiFlashProvider
    register("google-gemini-2.0-flash", GoogleGeminiFlashProvider, model="gemini-2.0-flash")

    from tool.LLM.logic.models.ernie_speed_8k.providers.baidu.interface import BaiduERNIESpeedProvider
    register("baidu-ernie-speed-8k", BaiduERNIESpeedProvider, model="ernie-speed-8k")

    from tool.LLM.logic.models.hunyuan_lite.providers.tencent.interface import TencentHunyuanLiteProvider
    register("tencent-hunyuan-lite", TencentHunyuanLiteProvider, model="hunyuan-lite")

    from tool.LLM.logic.models.qwen25_7b.providers.siliconflow.interface import SiliconFlowQwenProvider
    register("siliconflow-qwen2.5-7b", SiliconFlowQwenProvider, model="qwen2.5-7b")

    from tool.LLM.logic.auto import AutoProvider
    register("auto", AutoProvider)
