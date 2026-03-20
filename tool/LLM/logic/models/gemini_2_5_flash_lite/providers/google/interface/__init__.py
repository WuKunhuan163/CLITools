"""Gemini 2.5 Flash-Lite via Google AI Studio (OpenAI-compatible endpoint).

Endpoint: https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
Model:    gemini-2.5-flash-lite
Free tier available (rate-limited). Paid: $0.1/M in, $0.4/M out.
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import google as vendor


class GoogleGemini25FlashLiteProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "gemini-2.5-flash-lite"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 30
    DEFAULT_MAX_CONTEXT = 1048576
    DEFAULT_MAX_OUTPUT = 8192

    name = "google-gemini-2.5-flash-lite"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=True,
        supports_streaming=True,
        max_context_tokens=1048576,
        max_output_tokens=8192,
    )
