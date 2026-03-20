"""DeepSeek V3.2 Chat via DeepSeek API (OpenAI-compatible).

Endpoint: https://api.deepseek.com/chat/completions
Model:    deepseek-chat
Pricing:  $0.28/M input (cache miss), $0.028/M (cache hit), $0.42/M output

Non-thinking mode of DeepSeek V3.2. 128K context.
"""
from tool.LLM.logic.base.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import deepseek as vendor


class DeepSeekChatProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "deepseek-chat"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 60
    DEFAULT_MAX_CONTEXT = 128000
    DEFAULT_MAX_OUTPUT = 8192

    name = "deepseek-chat"
    cost_model = CostModel(
        free_tier=False,
        prompt_price_per_m=0.28,
        completion_price_per_m=0.42,
    )
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=False,
        supports_streaming=True,
        max_context_tokens=128000,
        max_output_tokens=8192,
    )
