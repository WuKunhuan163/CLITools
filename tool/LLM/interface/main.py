"""LLM Tool Interface -- cross-tool access to LLM providers.

Other tools access LLM capabilities via:
    from tool.LLM.interface.main import get_provider, send, SessionContext
"""
from tool.LLM.logic.base import LLMProvider, CostModel  # noqa: F401
from tool.LLM.logic.rate_limiter import RateLimiter, retry_on_transient  # noqa: F401
from tool.LLM.logic.session_context import SessionContext  # noqa: F401
from tool.LLM.logic.registry import (  # noqa: F401
    get_provider,
    get_default_provider,
    list_providers,
    register,
)
from tool.LLM.logic.providers.nvidia_glm47 import (  # noqa: F401
    NvidiaGLM47Provider,
)
from tool.LLM.logic.providers.zhipu_glm4 import (  # noqa: F401
    ZhipuGLM4Provider,
)
from tool.LLM.logic.config import (  # noqa: F401
    load_config,
    save_config,
    get_config_value,
    set_config_value,
)
from tool.LLM.logic.usage import (  # noqa: F401
    record_usage,
    get_summary as get_usage_summary,
    get_daily_summary as get_daily_usage_summary,
)


def get_info():
    """Return basic tool info dict."""
    return {"name": "LLM", "version": "2.0.0"}


def send(message: str, system: str = "", provider_name: str = "nvidia_glm47",
         temperature: float = 0.7, max_tokens: int = 4096) -> dict:
    """Convenience: send a single message and return the result.

    Returns:
        {"ok": bool, "text": str, "usage": dict, "error": str|None}
    """
    provider = get_provider(provider_name)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": message})
    return provider.send(messages, temperature=temperature, max_tokens=max_tokens)
