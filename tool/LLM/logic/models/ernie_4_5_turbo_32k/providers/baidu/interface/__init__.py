"""ERNIE 4.5 Turbo 32K via Baidu Qianfan V2 API (OpenAI-compatible).

Same pricing as 128K variant but with 32K context. Has batch discount.
0.8 CNY/M input, 3.2 CNY/M output.
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import baidu as vendor


class BaiduERNIE45Turbo32KProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "ernie-4.5-turbo-32k"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 300
    DEFAULT_MAX_CONTEXT = 32768
    DEFAULT_MAX_OUTPUT = 4096
    MAX_TOKENS_PARAM = "max_completion_tokens"

    name = "baidu-ernie-4.5-turbo-32k"
    cost_model = CostModel(free_tier=False)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=False,
        supports_streaming=True,
        max_context_tokens=32768,
        max_output_tokens=4096,
    )
