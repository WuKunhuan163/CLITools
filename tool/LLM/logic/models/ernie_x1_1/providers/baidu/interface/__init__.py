"""ERNIE X1.1 Preview via Baidu Qianfan V2 API (OpenAI-compatible).

Latest reasoning model from Baidu. 1 CNY/M input, 4 CNY/M output.
128K context window. Supports search enhancement.
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import baidu as vendor


class BaiduERNIEX11Provider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "ernie-x1.1-preview"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 200
    DEFAULT_MAX_CONTEXT = 131072
    DEFAULT_MAX_OUTPUT = 4096
    MAX_TOKENS_PARAM = "max_completion_tokens"

    name = "baidu-ernie-x1.1"
    cost_model = CostModel(free_tier=False)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=False,
        supports_streaming=True,
        max_context_tokens=131072,
        max_output_tokens=4096,
    )
