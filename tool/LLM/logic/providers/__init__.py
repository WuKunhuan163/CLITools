"""LLM provider implementations.

Each provider lives in its own package:
    providers/<name>/
        __init__.py      — package exports
        interface/       — API client (LLMProvider subclass)
        pipeline/        — context/tool transformation logic
"""
