"""Claude Sonnet 4.6 via Anthropic Messages API.

Endpoint: https://api.anthropic.com/v1/messages
Model:    claude-sonnet-4-6-20260101
Pricing:  $3/M input, $15/M output tokens

Flagship model for complex reasoning and coding tasks.
200K context window, vision support, tool calling.
"""
from tool.LLM.logic.anthropic_base import AnthropicProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities


class AnthropicClaudeSonnetProvider(AnthropicProvider):

    MODEL_ID = "claude-sonnet-4-6-20260101"
    DEFAULT_RPM = 50
    DEFAULT_MAX_CONTEXT = 200000
    DEFAULT_MAX_OUTPUT = 8192
    REQUEST_TIMEOUT = 120

    name = "anthropic-claude-sonnet-4.6"
    cost_model = CostModel(
        free_tier=False,
        prompt_price_per_m=3.0,
        completion_price_per_m=15.0,
    )
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=True,
        supports_streaming=True,
        max_context_tokens=200000,
        max_output_tokens=8192,
    )
