"""Gemini 3.1 Flash-Lite (Preview) via Google AI Studio (OpenAI-compatible endpoint).

Endpoint: https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
Model:    gemini-3.1-flash-lite-preview
Free tier available (rate-limited). Paid: $0.25/M in, $1.5/M out.
"""
from tool.LLM.logic.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import google as vendor


class GoogleGemini31FlashLiteProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "gemini-3.1-flash-lite-preview"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 30
    DEFAULT_MAX_CONTEXT = 1048576
    DEFAULT_MAX_OUTPUT = 8192

    name = "google-gemini-3.1-flash-lite"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=True,
        supports_streaming=True,
        max_context_tokens=1048576,
        max_output_tokens=8192,
    )
