"""Zhipu GLM-4.7-Flash provider package — direct Zhipu AI API.

Uses the zhipuai SDK (optional) or falls back to urllib for HTTP calls.
Model: glm-4.7-flash (MoE reasoning model, 128K context, free tier).

Key difference from glm-4-flash: This is a reasoning model that produces
a separate `reasoning_content` field. Reasoning tokens consume the
max_tokens budget, so higher default max_tokens is needed.
"""
