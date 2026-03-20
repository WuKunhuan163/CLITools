"""LLM Tool Interface -- cross-tool access to LLM providers.

Other tools access LLM capabilities via:
    from tool.LLM.interface.main import get_provider, send, SessionContext
"""
from tool.LLM.logic.base import LLMProvider, CostModel  # noqa: F401
from tool.LLM.logic.rate.limiter import RateLimiter, retry_on_transient  # noqa: F401
from tool.LLM.logic.session.context import SessionContext  # noqa: F401
from tool.LLM.logic.registry import (  # noqa: F401
    get_provider,
    get_default_provider,
    get_pipeline,
    list_providers,
    register,
    _ALIASES as provider_aliases,
)
from tool.LLM.logic.pipeline import ContextPipeline  # noqa: F401
from tool.LLM.logic.models.glm_4_7.providers.nvidia.interface import (  # noqa: F401
    NvidiaGLM47Provider,
    get_api_key as get_nvidia_api_key,
    save_api_key as save_nvidia_api_key,
)
from tool.LLM.logic.models.glm_4_flash.providers.zhipu.interface import (  # noqa: F401
    ZhipuGLM4Provider,
    get_api_key as get_zhipu_api_key,
    save_api_key as save_zhipu_api_key,
)
from tool.LLM.logic.config import (  # noqa: F401
    load_config,
    save_config,
    get_config_value,
    set_config_value,
    get_provider_config,
    set_provider_config,
)
from tool.LLM.logic.session.usage import (  # noqa: F401
    record_usage,
    get_summary as get_usage_summary,
    get_daily_summary as get_daily_usage_summary,
)


def get_info():
    """Return basic tool info dict."""
    return {"name": "LLM", "version": "2.0.0"}


def get_provider_guide(vendor: str) -> dict:
    """Load the setup guide for a provider vendor.

    Returns dict with keys: vendor, name, url, steps, notes.
    Falls back to a generic guide if no vendor-specific file exists.
    """
    import json
    from pathlib import Path
    guide_path = Path(__file__).resolve().parent.parent / "logic" / "providers" / "guides" / f"{vendor}.json"
    if guide_path.exists():
        try:
            return json.loads(guide_path.read_text())
        except Exception:
            pass
    return {
        "vendor": vendor,
        "name": vendor.title(),
        "url": "",
        "steps": [
            "Visit the provider's official website",
            "Register for an account",
            "Navigate to API Keys section",
            "Generate and copy your API key",
            "Paste it in the configuration",
        ],
        "notes": "",
    }


def get_model_metadata(model_dir_name: str) -> dict:
    """Load model.json for a model directory name (e.g. 'glm_4_flash').

    Returns the full model metadata including active state and lock_reason.
    """
    import json
    from pathlib import Path
    model_json = Path(__file__).resolve().parent.parent / "logic" / "models" / model_dir_name / "model.json"
    if model_json.exists():
        try:
            return json.loads(model_json.read_text())
        except Exception:
            pass
    return {}


def is_model_active(model_dir_name: str) -> bool:
    """Check if a model is marked as active in its model.json."""
    meta = get_model_metadata(model_dir_name)
    return meta.get("active", True)


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

    This HTML loads ``engine.js`` which provides the
    ``AgentGUIEngine`` class with block registry, theme override,
    and SSE support for real-time streaming.

    Returns:
        Absolute path to ``demo.html``.
    """
    from pathlib import Path
    return str(Path(__file__).resolve().parent.parent / "logic" / "gui" / "demo.html")


def get_engine_path() -> str:
    """Return absolute path to the reusable agent GUI JS engine.

    The engine provides ``AgentGUIEngine`` with:
    - Block registry: ``engine.registerBlock(type, renderFn)``
    - Theme override: ``engine.loadTheme({accent: '#e63946'})``
    - SSE connection: ``engine.connectSSE('/api/events')``
    - Protocol event processing: ``engine.processEvent(evt)``

    Returns:
        Absolute path to ``engine.js``.
    """
    from pathlib import Path
    return str(Path(__file__).resolve().parent.parent / "logic" / "gui" / "engine.js")


def get_conversation_manager():
    """Return the ConversationManager class for building agent GUIs.

    The ConversationManager is a GUI-agnostic stateful conversation
    orchestrator. All GUI variants (HTML, CLI, tkinter) use the same
    interface. Events are dispatched via callback in the protocol
    format expected by ``AgentGUIEngine``.

    Usage::

        from tool.LLM.interface.main import get_conversation_manager
        ConversationManager = get_conversation_manager()

        mgr = ConversationManager(selected_model="auto")
        mgr.on_event(lambda evt: push_to_gui(evt))
        sid = mgr.new_session()
        mgr.send_message(sid, "Hello!")

    Returns:
        The ``ConversationManager`` class.
    """
    from tool.LLM.logic.task.agent.conversation import ConversationManager
    return ConversationManager


def get_live_path() -> str:
    """Return absolute path to the live LLM agent HTML page.

    Returns:
        Absolute path to ``live.html``.
    """
    from pathlib import Path
    return str(Path(__file__).resolve().parent.parent / "logic" / "gui" / "live.html")


def get_brain(data_dir=None):
    """Get a Brain instance for LLM memory management.

    The Brain manages memory across sessions:
    - Working memory (AgentEnvironment)
    - Short-term memory (SessionContext)
    - Long-term memory (MemoryStore)

    Override in Openclaw for self-evolving capabilities.

    Parameters
    ----------
    data_dir : Path, optional
        Directory for persistent memory storage.

    Returns:
        A ``Brain`` instance.
    """
    from tool.LLM.logic.session.brain import Brain
    return Brain(data_dir=data_dir)


def start_server(selected_model="auto", port=0,
                       open_browser=True, enable_tools=False,
                       default_codebase=None, brain=None):
    """Start the live LLM Agent server.

    Returns an ``AgentServer`` instance with the server already running.
    """
    from logic.assistant.gui.server import start_server as _start
    return _start(
        selected_model=selected_model,
        port=port,
        open_browser=open_browser,
        enable_tools=enable_tools,
        default_codebase=default_codebase,
        brain=brain,
    )


def generate_dashboard():
    """Generate the LLM usage dashboard data."""
    from tool.LLM.logic.dashboard.generate import generate
    return generate()


def get_dashboard_path() -> str:
    """Return absolute path to the LLM usage dashboard HTML template.

    Returns:
        Absolute path to ``template.html``.
    """
    from pathlib import Path
    return str(Path(__file__).resolve().parent.parent / "logic" / "dashboard" / "template.html")
