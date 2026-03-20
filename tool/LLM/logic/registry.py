"""LLM provider registry.

Central point for discovering, configuring, and instantiating LLM providers.
Structure: models/<model>/main.py with model.json at model level.

Registry names follow the pattern: <vendor>-<model_key> (e.g. "zhipu-glm-4-flash").
Model-level resolution: "glm-4-flash" resolves to the preferred provider.

See naming.py for the full naming convention documentation.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from tool.LLM.logic.base import LLMProvider
from tool.LLM.logic.naming import model_key_to_dir, build_model_key_index
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


def _build_model_json_index() -> Dict[str, dict]:
    """Scan all model directories and index model.json by multiple keys.

    Uses naming convention: dir_name = model_key_to_dir(model_key).
    """
    index: Dict[str, dict] = {}
    if not _MODELS_DIR.is_dir():
        return index
    for d in _MODELS_DIR.iterdir():
        if not d.is_dir() or d.name.startswith("_"):
            continue
        mj = d / "model.json"
        if mj.exists():
            try:
                data = json.loads(mj.read_text())
                model_id = data.get("model_id", "")
                if model_id:
                    index[model_id] = data
                    index[model_key_to_dir(model_id)] = data
                api_id = data.get("api_model_id", "")
                if api_id and api_id != model_id:
                    index[api_id] = data
                index[d.name] = data
                dn = data.get("display_name", "")
                if dn:
                    norm = dn.lower().replace(" ", "-")
                    index[norm] = data
            except Exception:
                pass
    return index


def list_models() -> List[Dict[str, Any]]:
    """Return info for each model with its available providers."""
    _ensure_builtins()
    idx = _build_model_json_index()
    results = []
    for model, providers in _MODEL_PROVIDERS.items():
        meta = idx.get(model, {})
        if not meta:
            meta = idx.get(model_key_to_dir(model), {})
        entry = {
            "model": model,
            "display_name": meta.get("display_name", model),
            "vendor": meta.get("vendor", ""),
            "providers": providers,
            "capabilities": meta.get("capabilities", {}),
            "cost": meta.get("cost", {}),
        }
        lb = meta.get("logo_brightness")
        if lb is not None:
            entry["logo_brightness"] = lb
        results.append(entry)
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
    "gemini-flash": "google-gemini-2.5-flash",
    "gemini": "google-gemini-2.5-flash",
    "gemini-2.5-flash": "google-gemini-2.5-flash",
    "gemini-flash-lite": "google-gemini-2.5-flash-lite",
    "gemini-2.5-flash-lite": "google-gemini-2.5-flash-lite",
    "gemini-pro": "google-gemini-2.5-pro",
    "gemini-2.5-pro": "google-gemini-2.5-pro",
    "gemini-3-flash": "google-gemini-3-flash",
    "gemini-3.1-flash-lite": "google-gemini-3.1-flash-lite",
    "gemini-3.1-pro": "google-gemini-3.1-pro",
    "ernie-speed-8k": "baidu-ernie-speed-8k",
    "ernie-speed": "baidu-ernie-speed-8k",
    "ernie-speed-pro-128k": "baidu-ernie-speed-8k",
    "ernie-speed-pro": "baidu-ernie-speed-8k",
    "ernie-4.5-turbo": "baidu-ernie-4.5-turbo-128k",
    "ernie-4.5-turbo-128k": "baidu-ernie-4.5-turbo-128k",
    "ernie-turbo": "baidu-ernie-4.5-turbo-128k",
    "ernie-5.0": "baidu-ernie-5.0",
    "ernie-5": "baidu-ernie-5.0",
    "ernie-4.5-8k": "baidu-ernie-4.5-8k",
    "ernie-4.5-8k-preview": "baidu-ernie-4.5-8k",
    "ernie-4.5": "baidu-ernie-4.5-8k",
    "ernie-x1-turbo": "baidu-ernie-x1-turbo-32k",
    "ernie-x1-turbo-32k": "baidu-ernie-x1-turbo-32k",
    "ernie-x1.1": "baidu-ernie-x1.1",
    "ernie-x1.1-preview": "baidu-ernie-x1.1",
    "ernie-4.0-turbo-8k": "baidu-ernie-4.0-turbo-8k",
    "ernie-4.0-turbo": "baidu-ernie-4.0-turbo-8k",
    "ernie-4.5-turbo-32k": "baidu-ernie-4.5-turbo-32k",
    "hunyuan-lite": "tencent-hunyuan-lite",
    "qwen2.5-7b": "siliconflow-qwen2.5-7b",
    "qwen-2.5-7b": "siliconflow-qwen2.5-7b",
    "siliconflow-qwen": "siliconflow-qwen2.5-7b",
    "claude-sonnet": "anthropic-claude-sonnet-4.6",
    "claude-sonnet-4.6": "anthropic-claude-sonnet-4.6",
    "claude-4.6": "anthropic-claude-sonnet-4.6",
    "claude": "anthropic-claude-sonnet-4.6",
    "claude-haiku": "anthropic-claude-haiku-4.5",
    "claude-haiku-4.5": "anthropic-claude-haiku-4.5",
    "gpt-4o": "openai-gpt-4o",
    "gpt4o": "openai-gpt-4o",
    "gpt-4o-mini": "openai-gpt-4o-mini",
    "gpt4o-mini": "openai-gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "deepseek-v3": "deepseek-chat",
    "deepseek-think": "deepseek-reasoner",
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


def fuzzy_resolve(name: str) -> Optional[str]:
    """Try to resolve a model/provider name using fuzzy matching.

    Returns the resolved registry name, or None if no match found.
    Useful for Auto decision fault tolerance.
    """
    from tool.LLM.logic.naming import fuzzy_match_model
    _ensure_builtins()

    if name in _REGISTRY or name in _ALIASES:
        return _resolve(name)

    all_keys = list(_REGISTRY.keys()) + list(_ALIASES.keys()) + list(_MODEL_PROVIDERS.keys())
    match = fuzzy_match_model(name, all_keys, threshold=0.55)
    if match:
        return _resolve(match)
    return None


def get_provider(name: str = "zhipu-glm-4-flash", **kwargs) -> LLMProvider:
    """Get a provider instance by name or model name.

    Falls back to fuzzy matching if exact resolution fails.

    Raises:
        ValueError: If the provider name is not registered.
    """
    _ensure_builtins()
    resolved = _resolve(name)
    if resolved not in _REGISTRY:
        fuzzy = fuzzy_resolve(name)
        if fuzzy and fuzzy in _REGISTRY:
            resolved = fuzzy
        else:
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

    from tool.LLM.logic.models.glm_4_flash.main import ZhipuGLM4Provider
    from tool.LLM.logic.models.glm_4_flash.pipeline import ZhipuContextPipeline
    register("zhipu-glm-4-flash", ZhipuGLM4Provider, ZhipuContextPipeline(), model="glm-4-flash")

    from tool.LLM.logic.models.glm_4_7.nvidia import NvidiaGLM47Provider
    from tool.LLM.logic.models.glm_4_7.nvidia import NvidiaContextPipeline
    register("nvidia-glm-4-7b", NvidiaGLM47Provider, NvidiaContextPipeline(), model="glm-4.7")

    from tool.LLM.logic.models.glm_4_7.main import ZhipuGLM47Provider
    from tool.LLM.logic.models.glm_4_7.main import ZhipuGLM47Pipeline
    register("zhipu-glm-4.7", ZhipuGLM47Provider, ZhipuGLM47Pipeline(), model="glm-4.7")

    from tool.LLM.logic.models.glm_4_7_flash.main import ZhipuGLM47FlashProvider
    from tool.LLM.logic.models.glm_4_7_flash.pipeline import ZhipuGLM47FlashPipeline
    register("zhipu-glm-4.7-flash", ZhipuGLM47FlashProvider, ZhipuGLM47FlashPipeline(), model="glm-4.7-flash")

    from tool.LLM.logic.models.gemini_2_5_flash.main import GoogleGemini25FlashProvider
    register("google-gemini-2.5-flash", GoogleGemini25FlashProvider, model="gemini-2.5-flash")

    from tool.LLM.logic.models.gemini_2_5_flash_lite.main import GoogleGemini25FlashLiteProvider
    register("google-gemini-2.5-flash-lite", GoogleGemini25FlashLiteProvider, model="gemini-2.5-flash-lite")

    from tool.LLM.logic.models.gemini_2_5_pro.main import GoogleGemini25ProProvider
    register("google-gemini-2.5-pro", GoogleGemini25ProProvider, model="gemini-2.5-pro")

    from tool.LLM.logic.models.gemini_3_flash.main import GoogleGemini3FlashProvider
    register("google-gemini-3-flash", GoogleGemini3FlashProvider, model="gemini-3-flash")

    from tool.LLM.logic.models.gemini_3_1_flash_lite.main import GoogleGemini31FlashLiteProvider
    register("google-gemini-3.1-flash-lite", GoogleGemini31FlashLiteProvider, model="gemini-3.1-flash-lite")

    from tool.LLM.logic.models.gemini_3_1_pro.main import GoogleGemini31ProProvider
    register("google-gemini-3.1-pro", GoogleGemini31ProProvider, model="gemini-3.1-pro")

    from tool.LLM.logic.models.ernie_speed_8k.main import BaiduERNIESpeedProvider
    register("baidu-ernie-speed-8k", BaiduERNIESpeedProvider, model="ernie-speed-8k")

    from tool.LLM.logic.models.ernie_4_5_turbo_128k.main import BaiduERNIE45TurboProvider
    register("baidu-ernie-4.5-turbo-128k", BaiduERNIE45TurboProvider, model="ernie-4.5-turbo-128k")

    from tool.LLM.logic.models.ernie_5_0.main import BaiduERNIE50Provider
    register("baidu-ernie-5.0", BaiduERNIE50Provider, model="ernie-5.0")

    from tool.LLM.logic.models.ernie_4_5_8k.main import BaiduERNIE45Provider
    register("baidu-ernie-4.5-8k", BaiduERNIE45Provider, model="ernie-4.5-8k")

    from tool.LLM.logic.models.ernie_x1_turbo_32k.main import BaiduERNIEX1TurboProvider
    register("baidu-ernie-x1-turbo-32k", BaiduERNIEX1TurboProvider, model="ernie-x1-turbo-32k")

    from tool.LLM.logic.models.ernie_x1_1.main import BaiduERNIEX11Provider
    register("baidu-ernie-x1.1", BaiduERNIEX11Provider, model="ernie-x1.1")

    from tool.LLM.logic.models.ernie_4_0_turbo_8k.main import BaiduERNIE40TurboProvider
    register("baidu-ernie-4.0-turbo-8k", BaiduERNIE40TurboProvider, model="ernie-4.0-turbo-8k")

    from tool.LLM.logic.models.ernie_4_5_turbo_32k.main import BaiduERNIE45Turbo32KProvider
    register("baidu-ernie-4.5-turbo-32k", BaiduERNIE45Turbo32KProvider, model="ernie-4.5-turbo-32k")

    from tool.LLM.logic.models.hunyuan_lite.main import TencentHunyuanLiteProvider
    register("tencent-hunyuan-lite", TencentHunyuanLiteProvider, model="hunyuan-lite")

    from tool.LLM.logic.models.qwen2_5_7b.main import SiliconFlowQwenProvider
    register("siliconflow-qwen2.5-7b", SiliconFlowQwenProvider, model="qwen2.5-7b")

    from tool.LLM.logic.models.claude_sonnet_4_6.main import AnthropicClaudeSonnetProvider
    register("anthropic-claude-sonnet-4.6", AnthropicClaudeSonnetProvider, model="claude-sonnet-4.6")

    from tool.LLM.logic.models.claude_haiku_4_5.main import AnthropicClaudeHaikuProvider
    register("anthropic-claude-haiku-4.5", AnthropicClaudeHaikuProvider, model="claude-haiku-4.5")

    from tool.LLM.logic.models.gpt_4o.main import OpenAIGPT4oProvider
    register("openai-gpt-4o", OpenAIGPT4oProvider, model="gpt-4o")

    from tool.LLM.logic.models.gpt_4o_mini.main import OpenAIGPT4oMiniProvider
    register("openai-gpt-4o-mini", OpenAIGPT4oMiniProvider, model="gpt-4o-mini")

    from tool.LLM.logic.models.deepseek_chat.main import DeepSeekChatProvider
    register("deepseek-chat", DeepSeekChatProvider, model="deepseek-chat")

    from tool.LLM.logic.models.deepseek_reasoner.main import DeepSeekReasonerProvider
    register("deepseek-reasoner", DeepSeekReasonerProvider, model="deepseek-reasoner")

    from tool.LLM.logic.base.auto import AutoProvider
    register("auto", AutoProvider)
