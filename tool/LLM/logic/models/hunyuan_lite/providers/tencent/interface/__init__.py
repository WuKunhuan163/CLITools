"""Tencent Hunyuan Lite via Tencent Cloud (OpenAI-compatible endpoint).

Free tier: 5 QPS (permanently free).
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import tencent as vendor


class TencentHunyuanLiteProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "hunyuan-lite"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
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
