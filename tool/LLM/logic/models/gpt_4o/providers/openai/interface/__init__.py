"""GPT-4o via OpenAI Chat Completions API.

Endpoint: https://api.openai.com/v1/chat/completions
Model:    gpt-4o
Pricing:  $2.50/M input, $10/M output tokens

Multimodal flagship model. 128K context, vision, tool calling.
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import openai as vendor


class OpenAIGPT4oProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "gpt-4o"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 500
    DEFAULT_MAX_CONTEXT = 128000
    DEFAULT_MAX_OUTPUT = 16384

    name = "openai-gpt-4o"
    cost_model = CostModel(
        free_tier=False,
        prompt_price_per_m=2.50,
        completion_price_per_m=10.0,
    )
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=True,
        supports_streaming=True,
        max_context_tokens=128000,
        max_output_tokens=16384,
    )
