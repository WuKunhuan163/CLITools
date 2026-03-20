# Hooks Base Interface — Agent Reference

## Classes

### OnToolStart
- **event_name**: `"on_tool_start"`
- **kwargs**: `tool` (ToolBase), `args` (argparse.Namespace or None)
- Fired after `ToolBase.__init__` and `handle_command_line` complete without early exit.

### OnToolExit
- **event_name**: `"on_tool_exit"`
- **kwargs**: `tool` (ToolBase), `exit_code` (int, 0=success), `error` (Exception or None)
- Fired when the tool's main execution finishes.

## Usage

These interfaces are discovered automatically by `HooksEngine` from `logic/tool/hooks/base/`. Tools fire them via `tool.fire_hook("on_tool_start", tool=self, args=args)`.

## Gotchas

- Do not add `__init__.py` here unless you need explicit exports; the engine loads modules by path.
- Instance handlers must declare `event_name` matching one of these to be valid (audit checks HOOK004).
