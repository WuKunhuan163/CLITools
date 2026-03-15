"""Zhipu GLM-4-Flash pipeline — model-specific context and tool management.

This module handles GLM-4-Flash quirks:
- Tool call history flattening (model returns empty when prior tool_calls in context)
- Response validation (detecting empty responses with non-zero completion tokens)
- Provider-specific prompt formatting
"""
from tool.LLM.logic.models.glm_4_flash.providers.zhipu.pipeline.context import ZhipuContextPipeline

__all__ = ["ZhipuContextPipeline"]
