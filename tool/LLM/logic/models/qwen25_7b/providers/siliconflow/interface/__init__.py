"""Qwen 2.5 7B via SiliconFlow platform (OpenAI-compatible endpoint).

Free tier: 3 RPS, 100 RPM (permanently free for select open-source models).
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import siliconflow as vendor


class SiliconFlowQwenProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 100
    DEFAULT_MAX_CONTEXT = 32768
    DEFAULT_MAX_OUTPUT = 4096

    name = "siliconflow-qwen2.5-7b"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=False,
        supports_streaming=True,
        max_context_tokens=32768,
        max_output_tokens=4096,
    )
