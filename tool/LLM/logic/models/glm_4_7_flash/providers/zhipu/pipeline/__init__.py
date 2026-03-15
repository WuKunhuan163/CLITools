"""Zhipu GLM-4.7-Flash pipeline — reasoning model context and tool management.

GLM-4.7-Flash is based on GLM-4.7 (more capable than GLM-4-Flash) but is a
reasoning model: responses include reasoning_content separate from content.
This pipeline handles:
- Reasoning token budget awareness (reasoning consumes max_tokens)
- Multi-turn context flattening (inherited from GLM-4-Flash pipeline as safety)
- Response validation for empty content when reasoning was produced
"""
from tool.LLM.logic.models.glm_4_7_flash.providers.zhipu.pipeline.context import (
    ZhipuGLM47FlashPipeline,
)

__all__ = ["ZhipuGLM47FlashPipeline"]
