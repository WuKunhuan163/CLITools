"""ERNIE 4.5 Turbo 128K via Baidu Qianfan V2 API (OpenAI-compatible).

Cheapest ERNIE model: 0.8 CNY/M input, 3.2 CNY/M output.
128K context window. Supports search enhancement.
"""
from tool.LLM.logic.base.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import baidu as vendor


class BaiduERNIE45TurboProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "ernie-4.5-turbo-128k"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 300
    DEFAULT_MAX_CONTEXT = 131072
    DEFAULT_MAX_OUTPUT = 4096
    MAX_TOKENS_PARAM = "max_completion_tokens"
    STRICT_ALTERNATION = True

    name = "baidu-ernie-4.5-turbo-128k"
    cost_model = CostModel(free_tier=False)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=False,
        supports_streaming=True,
        max_context_tokens=131072,
        max_output_tokens=4096,
    )
