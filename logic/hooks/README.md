# Hooks

Event-driven callback system for tools. Discovers interfaces (events) and instances (handlers), loads config, and fires handlers when tools emit events.

## Purpose

Allows tools to extend behavior without modifying core logic. Tools fire events (e.g. on_tool_start, on_tool_exit); enabled instances execute in response. Configurable per tool via hooks/config.json.

## Structure

| Path | Responsibility |
|------|----------------|
| engine.py | HookInterface, HookInstance, HooksEngine |
| base/interface/ | Framework-level events (on_tool_start, on_tool_exit) |
| base/instance/ | Framework-level instances (currently empty) |

## Key Exports

- `HookInterface`, `HookInstance` — base classes
- `HooksEngine` — per-tool manager (discover, enable/disable, fire)
