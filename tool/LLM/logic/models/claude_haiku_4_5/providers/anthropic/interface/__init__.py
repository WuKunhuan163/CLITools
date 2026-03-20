"""Claude Haiku 4.5 via Anthropic Messages API.

Endpoint: https://api.anthropic.com/v1/messages
Model:    claude-haiku-4-5-20260101
Pricing:  $1/M input, $5/M output tokens

Fast, affordable model for high-throughput tasks.
200K context window, vision support, tool calling.
"""
from tool.LLM.logic.anthropic_base import AnthropicProvider
from tool.LLM.logic.base import CostModel, ModelCapabilities


class AnthropicClaudeHaikuProvider(AnthropicProvider):

    MODEL_ID = "claude-haiku-4-5-20260101"
    DEFAULT_RPM = 50
    DEFAULT_MAX_CONTEXT = 200000
    DEFAULT_MAX_OUTPUT = 8192
    REQUEST_TIMEOUT = 60

    name = "anthropic-claude-haiku-4.5"
    cost_model = CostModel(
        free_tier=False,
        prompt_price_per_m=1.0,
        completion_price_per_m=5.0,
    )
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=True,
        supports_streaming=True,
        max_context_tokens=200000,
        max_output_tokens=8192,
    )
