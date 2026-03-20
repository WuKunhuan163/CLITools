"""ERNIE X1-Turbo 32K via Baidu Qianfan V2 API (OpenAI-compatible).

Budget reasoning model. 1 CNY/M input, 4 CNY/M output.
32K context window. Deep thinking capability.
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import baidu as vendor


class BaiduERNIEX1TurboProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "ernie-x1-turbo-32k"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 300
    DEFAULT_MAX_CONTEXT = 32768
    DEFAULT_MAX_OUTPUT = 4096
    MAX_TOKENS_PARAM = "max_completion_tokens"

    name = "baidu-ernie-x1-turbo-32k"
    cost_model = CostModel(free_tier=False)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=False,
        supports_streaming=True,
        max_context_tokens=32768,
        max_output_tokens=4096,
    )
