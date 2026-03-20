"""Baidu ERNIE Speed Pro 128K via Qianfan v2 platform (OpenAI-compatible endpoint).

Free tier: 10000 RPM, 800K TPM (permanently free for Speed/Lite series).

Note: The old 'ernie-speed-8k' was retired from v2 API. The current free Speed
model is 'ernie-speed-pro-128k'. Our internal name stays 'ernie-speed-8k' for
backwards compatibility in the provider registry.
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import baidu as vendor


class BaiduERNIESpeedProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "ernie-speed-pro-128k"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 10000
    DEFAULT_MAX_CONTEXT = 131072
    DEFAULT_MAX_OUTPUT = 4096
    MAX_TOKENS_PARAM = "max_completion_tokens"

    name = "baidu-ernie-speed-8k"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=False,
        supports_streaming=True,
        max_context_tokens=131072,
        max_output_tokens=4096,
    )
