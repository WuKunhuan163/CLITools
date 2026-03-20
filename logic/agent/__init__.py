"""Agent infrastructure — turns any tool into an autonomous agent.

Provides the core agent loop, context building, tool schema generation,
session state management, and feed protocol. Each tool can extend this
with tool-specific skills and handlers via ``tool/<NAME>/logic/agent/``.

Usage from ToolBase:
    self._handle_agent_command(args)  # dispatches --agent subcommands
"""
