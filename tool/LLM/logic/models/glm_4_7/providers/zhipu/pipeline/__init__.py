"""Zhipu GLM-4.7 pipeline — model-specific context and tool management.

GLM-4.7 is a significantly more capable model than GLM-4-Flash. It
handles multi-turn tool calling natively without the empty-response
bug. Currently a pass-through pipeline.
"""
from tool.LLM.logic.models.glm_4_7.providers.zhipu.pipeline.context import ZhipuGLM47Pipeline
