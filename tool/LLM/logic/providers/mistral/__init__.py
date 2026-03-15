"""Mistral provider — placeholder (assets only, not yet implemented)."""
from tool.LLM.logic.base import LLMProvider, ProviderNotImplementedError, CostModel, ModelCapabilities


class MistralProvider(LLMProvider):
    name = "mistral"
    cost_model = CostModel(free_tier=False, prompt_price_per_m=0.25, completion_price_per_m=0.25)
    capabilities = ModelCapabilities(
        supports_tool_calling=True, supports_vision=False,
        supports_streaming=True, max_context_tokens=32000,
    )

    def __init__(self, **kwargs):
        raise ProviderNotImplementedError("Mistral provider not yet implemented")

    def _send_request(self, messages, temperature=1.0, max_tokens=16384, tools=None):
        raise ProviderNotImplementedError("Mistral provider not yet implemented")

    def is_available(self):
        return False
