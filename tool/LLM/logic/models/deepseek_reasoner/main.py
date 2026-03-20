"""DeepSeek V3.2 Reasoner via DeepSeek API (OpenAI-compatible).

Endpoint: https://api.deepseek.com/chat/completions
Model:    deepseek-reasoner
Pricing:  $0.28/M input, $0.42/M output tokens

Thinking mode of DeepSeek V3.2. Produces reasoning_content.
128K context, 64K max output.
"""
from tool.LLM.logic.base.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import deepseek as vendor


class DeepSeekReasonerProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "deepseek-reasoner"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 60
    DEFAULT_MAX_CONTEXT = 128000
    DEFAULT_MAX_OUTPUT = 65536

    name = "deepseek-reasoner"
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
        max_output_tokens=65536,
    )
