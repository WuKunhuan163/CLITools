"""OpenAI provider — placeholder (assets only, not yet implemented)."""
from tool.LLM.logic.base import LLMProvider, ProviderNotImplementedError, CostModel, ModelCapabilities


class OpenAIProvider(LLMProvider):
    name = "openai"
    cost_model = CostModel(free_tier=False, prompt_price_per_m=2.5, completion_price_per_m=10.0)
    capabilities = ModelCapabilities(
        supports_tool_calling=True, supports_vision=True,
        supports_streaming=True, max_context_tokens=128000,
    )

    def __init__(self, **kwargs):
        raise ProviderNotImplementedError("OpenAI provider not yet implemented")

    def _send_request(self, messages, temperature=1.0, max_tokens=16384, tools=None):
        raise ProviderNotImplementedError("OpenAI provider not yet implemented")

    def is_available(self):
        return False
