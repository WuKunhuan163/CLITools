"""Google (Gemini) provider — placeholder (assets only, not yet implemented)."""
from tool.LLM.logic.base import LLMProvider, ProviderNotImplementedError, CostModel, ModelCapabilities


class GoogleProvider(LLMProvider):
    name = "google"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=True, supports_vision=True,
        supports_streaming=True, max_context_tokens=1000000,
    )

    def __init__(self, **kwargs):
        raise ProviderNotImplementedError("Google/Gemini provider not yet implemented")

    def _send_request(self, messages, temperature=1.0, max_tokens=16384, tools=None):
        raise ProviderNotImplementedError("Google/Gemini provider not yet implemented")

    def is_available(self):
        return False
