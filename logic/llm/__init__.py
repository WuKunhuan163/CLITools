"""Shared LLM provider infrastructure for AITerminalTools.

Provides a unified interface for calling LLM APIs from any tool.
Inspired by OpenClaw's architecture: decision center (brain) communicates
with LLMs via clean API contracts, never touching web UIs directly.

Providers:
  - ``nvidia_glm47``: GLM-4.7 via NVIDIA Build (free tier, OpenAI-compatible)

Usage:
    from logic.llm.registry import get_provider, list_providers

    provider = get_provider("nvidia_glm47")
    result = provider.send([
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ])
    print(result["text"])
"""
