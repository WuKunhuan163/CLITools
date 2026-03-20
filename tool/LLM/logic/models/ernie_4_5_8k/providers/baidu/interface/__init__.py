"""ERNIE 4.5 8K via Baidu Qianfan V2 API (OpenAI-compatible).

Standard ERNIE model with 8K context. Vision-capable.
4 CNY/M input, 16 CNY/M output.
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import baidu as vendor


class BaiduERNIE45Provider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "ernie-4.5-8k-preview"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 300
    DEFAULT_MAX_CONTEXT = 8192
    DEFAULT_MAX_OUTPUT = 4096
    MAX_TOKENS_PARAM = "max_completion_tokens"
    STRICT_ALTERNATION = True

    name = "baidu-ernie-4.5-8k"
    cost_model = CostModel(free_tier=False)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=True,
        supports_streaming=True,
        max_context_tokens=8192,
        max_output_tokens=4096,
    )
