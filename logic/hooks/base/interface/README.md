# Hooks Base Interface

Base hook event definitions shared across all tools. These interfaces declare lifecycle events that tools can fire and hook instances can handle.

## Purpose

Defines the canonical set of hook events available to every tool. Tool-specific interfaces live in `<TOOL>/hooks/interface/`; this directory provides framework-level events.

## Structure

| File | Event | Description |
|------|-------|-------------|
| on_tool_start.py | on_tool_start | Fired when main() begins, after init and handle_command_line |
| on_tool_exit.py | on_tool_exit | Fired when main execution completes (success or failure) |

## Key Exports

- `OnToolStart` (HookInterface subclass)
- `OnToolExit` (HookInterface subclass)
