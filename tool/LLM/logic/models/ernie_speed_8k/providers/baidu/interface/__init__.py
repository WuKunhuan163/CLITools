"""Baidu ERNIE Speed 8K via Qianfan platform (OpenAI-compatible endpoint).

Endpoint: https://qianfan.baidubce.com/v2/chat/completions
Free tier: 300 RPM, 300K TPM (permanently free for Speed/Lite/Tiny series).
Requires: Baidu Qianfan platform API key (domestic CN, real-name auth).
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities


class BaiduERNIESpeedProvider(OpenAICompatProvider):

    API_URL = "https://qianfan.baidubce.com/v2/chat/completions"
    MODEL_ID = "ernie-speed-8k"
    CONFIG_VENDOR = "baidu"
    CONFIG_KEY_ENV = "BAIDU_API_KEY"
    DEFAULT_RPM = 300
    DEFAULT_MAX_CONTEXT = 8192
    DEFAULT_MAX_OUTPUT = 4096

    name = "baidu-ernie-speed-8k"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=False,
        supports_streaming=True,
        max_context_tokens=8192,
        max_output_tokens=4096,
    )
