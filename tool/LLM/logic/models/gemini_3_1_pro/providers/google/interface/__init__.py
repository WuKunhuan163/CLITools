"""Gemini 3.1 Pro (Preview) via Google AI Studio (OpenAI-compatible endpoint).

Endpoint: https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
Model:    gemini-3.1-pro-preview
Paid only: $2.0/M in, $12.0/M out.
"""
from tool.LLM.logic.base.openai_compat import OpenAICompatProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities
from tool.LLM.logic.providers import google as vendor


class GoogleGemini31ProProvider(OpenAICompatProvider):

    API_URL = vendor.API_URL
    MODEL_ID = "gemini-3.1-pro-preview"
    CONFIG_VENDOR = vendor.CONFIG_VENDOR
    CONFIG_KEY_ENV = vendor.CONFIG_KEY_ENV
    DEFAULT_RPM = 10
    DEFAULT_MAX_CONTEXT = 1048576
    DEFAULT_MAX_OUTPUT = 8192

    name = "google-gemini-3.1-pro"
    cost_model = CostModel(
        free_tier=False,
        prompt_price_per_m=2.0,
        completion_price_per_m=12.0,
    )
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=True,
        supports_streaming=True,
        max_context_tokens=1048576,
        max_output_tokens=8192,
    )
