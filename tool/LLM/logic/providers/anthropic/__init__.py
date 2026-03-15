"""Anthropic provider — placeholder (assets only, not yet implemented)."""
from tool.LLM.logic.base import LLMProvider, ProviderNotImplementedError, CostModel, ModelCapabilities


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    cost_model = CostModel(free_tier=False, prompt_price_per_m=3.0, completion_price_per_m=15.0)
    capabilities = ModelCapabilities(
        supports_tool_calling=True, supports_vision=True,
        supports_streaming=True, max_context_tokens=200000,
    )

    def __init__(self, **kwargs):
        raise ProviderNotImplementedError("Anthropic provider not yet implemented")

    def _send_request(self, messages, temperature=1.0, max_tokens=16384, tools=None):
        raise ProviderNotImplementedError("Anthropic provider not yet implemented")

    def is_available(self):
        return False
