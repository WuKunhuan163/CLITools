"""Standard tool registry and context."""
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional


@dataclass
class ToolContext:
    """Shared context for standard tool execution."""
    emit: Callable[[dict], None]
    cwd: str = "."
    project_root: str = "."
    brain: object = None
    env_obj: object = None
    write_history: Dict[str, list] = field(default_factory=dict)
    dup_counts: Dict[str, int] = field(default_factory=dict)
    turn_writes: list = field(default_factory=list)
    turn_reads: list = field(default_factory=list)
    round_store: object = None
    session_id: str = ""
    round_num: int = 0


def _noop_emit(evt: dict):
    pass


STANDARD_TOOLS: Dict[str, Callable] = {}


def register_tool(name: str):
    def decorator(fn):
        STANDARD_TOOLS[name] = fn
        return fn
    return decorator


from logic.assistant.std import tools  # noqa: E402, F401
