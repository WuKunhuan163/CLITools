"""Zhipu GLM-4.7 context pipeline.

GLM-4.7 handles multi-turn tool calling correctly — no flattening
or special workarounds needed (unlike GLM-4-Flash). This pipeline
is currently a pass-through.
"""
from tool.LLM.logic.pipeline import ContextPipeline


class ZhipuGLM47Pipeline(ContextPipeline):
    """Pipeline for Zhipu GLM-4.7 — pass-through."""

    def get_max_retries(self) -> int:
        return 2
