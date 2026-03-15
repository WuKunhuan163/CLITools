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


def send(message: str, system: str = "", provider_name: str = "nvidia-glm-4-7b",
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


# ---------------------------------------------------------------------------
# GUI Blueprint Interface
# ---------------------------------------------------------------------------

def get_agent_gui_path() -> str:
    """Return absolute path to the LLM agent GUI HTML template.

    This HTML loads ``agent_gui_engine.js`` which provides the
    ``AgentGUIEngine`` class with block registry, theme override,
    and SSE support for real-time streaming.

    Returns:
        Absolute path to ``agent_demo.html``.
    """
    from pathlib import Path
    return str(Path(__file__).resolve().parent.parent / "logic" / "gui" / "agent_demo.html")


def get_agent_gui_engine_path() -> str:
    """Return absolute path to the reusable agent GUI JS engine.

    The engine provides ``AgentGUIEngine`` with:
    - Block registry: ``engine.registerBlock(type, renderFn)``
    - Theme override: ``engine.loadTheme({accent: '#e63946'})``
    - SSE connection: ``engine.connectSSE('/api/events')``
    - Protocol event processing: ``engine.processEvent(evt)``

    Returns:
        Absolute path to ``agent_gui_engine.js``.
    """
    from pathlib import Path
    return str(Path(__file__).resolve().parent.parent / "logic" / "gui" / "agent_gui_engine.js")


def get_conversation_manager():
    """Return the ConversationManager class for building agent GUIs.

    The ConversationManager is a GUI-agnostic stateful conversation
    orchestrator. All GUI variants (HTML, CLI, tkinter) use the same
    interface. Events are dispatched via callback in the protocol
    format expected by ``AgentGUIEngine``.

    Usage::

        from tool.LLM.interface.main import get_conversation_manager
        ConversationManager = get_conversation_manager()

        mgr = ConversationManager(provider_name="zhipu-glm-4-flash")
        mgr.on_event(lambda evt: push_to_gui(evt))
        sid = mgr.new_session()
        mgr.send_message(sid, "Hello!")

    Returns:
        The ``ConversationManager`` class.
    """
    from tool.LLM.logic.gui.conversation import ConversationManager
    return ConversationManager


def get_agent_live_path() -> str:
    """Return absolute path to the live LLM agent HTML page.

    Returns:
        Absolute path to ``agent_live.html``.
    """
    from pathlib import Path
    return str(Path(__file__).resolve().parent.parent / "logic" / "gui" / "agent_live.html")


def start_agent_server(provider_name="zhipu-glm-4-flash", port=0,
                       open_browser=True, enable_tools=False):
    """Start the live LLM Agent server.

    Returns an ``AgentServer`` instance with the server already running.
    """
    from tool.LLM.logic.gui.agent_server import start_agent_server as _start
    return _start(
        provider_name=provider_name,
        port=port,
        open_browser=open_browser,
        enable_tools=enable_tools,
    )


def get_dashboard_path() -> str:
    """Return absolute path to the LLM usage dashboard HTML template.

    Returns:
        Absolute path to ``template.html``.
    """
    from pathlib import Path
    return str(Path(__file__).resolve().parent.parent / "logic" / "dashboard" / "template.html")
