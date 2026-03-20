"""Public facade for the agent infrastructure.

Usage:
    from interface.agent import AgentLoop, AgentSession, AgentEnvironment

    session = AgentSession(tool_name="BILIBILI", codebase_root="/path/to/tool")
    loop = AgentLoop(session=session, provider_name="zhipu-glm-4.7",
                     system_prompt="You are an agent.", project_root="/path")
    result = loop.run_turn("Search for trending videos")

Modes:
    --agent  Full capabilities (read, write, exec, edit)
    --ask    Read-only exploration (no write/edit, exec restricted)
    --plan   Read-only planning (no write/edit/scripts)

Brain/Memory:
    from interface.agent import inject_bootstrap_context, write_memory, write_daily_note
"""
from logic.agent.state import (  # noqa: F401
    AgentSession,
    AgentEnvironment,
    save_session,
    load_session,
    list_sessions,
)
from logic.agent.loop import AgentLoop  # noqa: F401
from logic.agent.context import build_context, build_runtime_header  # noqa: F401
from logic.agent.tools import (  # noqa: F401
    BUILTIN_TOOL_DEFS,
    ToolHandlers,
    get_tool_defs_for_mode,
    _is_readonly_safe,
    _is_plan_safe,
)
from logic.agent.quality import check_write_quality  # noqa: F401
from logic.agent.nudge import should_nudge, build_nudge_message  # noqa: F401
from logic.agent.command import handle_agent_command  # noqa: F401
from logic.agent.brain import (  # noqa: F401
    inject_bootstrap_context,
    write_memory,
    write_daily_note,
    load_bootstrap,
    list_brain_types,
    ensure_experience_dir,
)
from logic.agent.export import export_session, import_session  # noqa: F401
from logic.agent.memory import MemoryHandlers, MEMORY_TOOL_DEFS  # noqa: F401
from logic.agent.ecosystem import (  # noqa: F401
    build_ecosystem_info,
    build_system_state,
    build_contextual_suggestions,
)
from logic.assistant.std import STANDARD_TOOLS, ToolContext  # noqa: F401
from logic.search.knowledge import KnowledgeManager  # noqa: F401
