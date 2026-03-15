"""Gemini 2.0 Flash via Google AI Studio (OpenAI-compatible endpoint).

Free tier: 15 RPM, 1M TPM, 1500 RPD.
Region-restricted: no CN/HK direct access.
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import google as vendor


class GoogleGeminiFlashProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "gemini-2.0-flash"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 15
    DEFAULT_MAX_CONTEXT = 1000000
    DEFAULT_MAX_OUTPUT = 8192

    name = "google-gemini-2.0-flash"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=True,
        supports_streaming=True,
        max_context_tokens=1000000,
        max_output_tokens=8192,
    )
