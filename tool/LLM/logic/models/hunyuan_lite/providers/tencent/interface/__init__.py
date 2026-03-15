"""Tencent Hunyuan Lite via Tencent Cloud (OpenAI-compatible endpoint).

Endpoint: https://api.hunyuan.cloud.tencent.com/v1/chat/completions
Free tier: 5 QPS (permanently free).
Requires: Tencent Cloud API key (domestic CN, real-name auth).
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities


class TencentHunyuanLiteProvider(OpenAICompatProvider):

    API_URL = "https://api.hunyuan.cloud.tencent.com/v1/chat/completions"
    MODEL_ID = "hunyuan-lite"
    CONFIG_VENDOR = "tencent"
    CONFIG_KEY_ENV = "TENCENT_API_KEY"
    DEFAULT_RPM = 60
    DEFAULT_MAX_CONTEXT = 4096
    DEFAULT_MAX_OUTPUT = 2048

    name = "tencent-hunyuan-lite"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=False,
        supports_vision=False,
        supports_streaming=True,
        max_context_tokens=4096,
        max_output_tokens=2048,
    )
