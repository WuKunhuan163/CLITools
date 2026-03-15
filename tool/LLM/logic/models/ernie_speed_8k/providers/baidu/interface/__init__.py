"""Baidu ERNIE 3.5 8K via Qianfan v2 platform (OpenAI-compatible endpoint).

Endpoint: https://qianfan.baidubce.com/v2/chat/completions
Free tier: 300 RPM, 300K TPM (permanently free for Speed/Lite/Tiny series).
Requires: Baidu Qianfan platform API key (bce-v3/ALTAK format, real-name auth).

Note: The model was renamed from 'ernie-speed-8k' to 'ernie-3.5-8k' in Baidu's
v2 API. Our internal name stays 'ernie-speed-8k' for backwards compatibility.
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities


class BaiduERNIESpeedProvider(OpenAICompatProvider):

    API_URL = "https://qianfan.baidubce.com/v2/chat/completions"
    MODEL_ID = "ernie-3.5-8k"
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
