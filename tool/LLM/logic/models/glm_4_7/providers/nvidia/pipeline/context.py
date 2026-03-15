"""NVIDIA GLM-4.7 context pipeline.

Currently a pass-through — NVIDIA GLM-4.7 handles multi-turn tool
calling correctly. Override if issues are discovered.
"""
from tool.LLM.logic.pipeline import ContextPipeline


class NvidiaContextPipeline(ContextPipeline):
    """Pipeline for NVIDIA GLM-4.7 — pass-through."""
    pass
