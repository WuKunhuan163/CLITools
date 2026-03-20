"""ERNIE 4.0 Turbo 8K via Baidu Qianfan V2 API (OpenAI-compatible).

Legacy model, still functional. 8K context window.
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import baidu as vendor


class BaiduERNIE40TurboProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "ernie-4.0-turbo-8k"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 300
    DEFAULT_MAX_CONTEXT = 8192
    DEFAULT_MAX_OUTPUT = 4096
    MAX_TOKENS_PARAM = "max_completion_tokens"
    STRICT_ALTERNATION = True

    name = "baidu-ernie-4.0-turbo-8k"
    cost_model = CostModel(free_tier=False)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=False,
        supports_streaming=True,
        max_context_tokens=8192,
        max_output_tokens=4096,
    )
