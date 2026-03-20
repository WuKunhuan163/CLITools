"""GPT-4o Mini via OpenAI Chat Completions API.

Endpoint: https://api.openai.com/v1/chat/completions
Model:    gpt-4o-mini
Pricing:  $0.15/M input, $0.60/M output tokens

Fast, affordable model. 128K context, vision, tool calling.
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import openai as vendor


class OpenAIGPT4oMiniProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "gpt-4o-mini"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 500
    DEFAULT_MAX_CONTEXT = 128000
    DEFAULT_MAX_OUTPUT = 16384

    name = "openai-gpt-4o-mini"
    cost_model = CostModel(
        free_tier=False,
        prompt_price_per_m=0.15,
        completion_price_per_m=0.60,
    )
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=True,
        supports_streaming=True,
        max_context_tokens=128000,
        max_output_tokens=16384,
    )
