"""ERNIE Speed 8K (Legacy) — replaced by ERNIE 4.5 Turbo 128K.

This model previously used the qianfan SDK. Now uses OpenAI-compatible API.
Kept for backward compatibility; model.json marks it as inactive.
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import baidu as vendor


class BaiduERNIESpeedProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "ernie-speed-pro-128k"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 300
    DEFAULT_MAX_CONTEXT = 131072
    DEFAULT_MAX_OUTPUT = 4096
    MAX_TOKENS_PARAM = "max_completion_tokens"
    STRICT_ALTERNATION = True

    name = "baidu-ernie-speed-8k"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=False,
        supports_streaming=True,
        max_context_tokens=131072,
        max_output_tokens=4096,
    )
