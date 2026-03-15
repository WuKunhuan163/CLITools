"""Standard tool implementations for AI assistants.

Each tool is a standalone function that takes (args, context) and returns
a result dict with {ok, output}. The context object provides emit(), cwd(),
and project_root for environment interaction.

Usage:
    from logic.assistant.std import STANDARD_TOOLS, ToolContext

    ctx = ToolContext(emit_fn=my_emit, cwd="/project", project_root="/project")
    result = STANDARD_TOOLS["exec"]({"command": "ls"}, ctx)
"""
from logic.assistant.std.registry import STANDARD_TOOLS, ToolContext

__all__ = ["STANDARD_TOOLS", "ToolContext"]
