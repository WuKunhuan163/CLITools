"""ERNIE 5.0 via Baidu Qianfan V2 API (OpenAI-compatible).

Baidu's flagship model with reasoning and vision capabilities.
6 CNY/M input, 24 CNY/M output (<=32K context).
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import baidu as vendor


class BaiduERNIE50Provider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "ernie-5.0"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 100
    DEFAULT_MAX_CONTEXT = 131072
    DEFAULT_MAX_OUTPUT = 4096
    MAX_TOKENS_PARAM = "max_completion_tokens"

    name = "baidu-ernie-5.0"
    cost_model = CostModel(free_tier=False)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=True,
        supports_streaming=True,
        max_context_tokens=131072,
        max_output_tokens=4096,
    )
