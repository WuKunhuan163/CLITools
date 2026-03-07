# Blueprint

Base classes for tool archetypes. All tools inherit from one of these blueprints.

## Purpose

Provides `ToolBase` (standard tools) and `MCPToolBase` (CDMCP browser-integrated tools) with shared behavior: path resolution, dependencies, hooks, CLI handling, setup, and MCP session management.

## Structure

| File | Class | Use Case |
|------|-------|----------|
| base.py | ToolBase | Standard CLI tools |
| mcp.py | MCPToolBase | Tools using CDMCP browser MCP |

## Key Exports

- `ToolBase` — canonical base for all tools
- `MCPToolBase` — extends ToolBase with session/overlay/interact
