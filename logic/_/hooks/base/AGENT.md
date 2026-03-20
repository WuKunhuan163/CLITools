# Hooks Base — Agent Reference

## Purpose

Contains framework-level HookInterface subclasses. HooksEngine discovers these from `logic/tool/hooks/base/interface/` and merges with tool-specific interfaces from `<TOOL>/hooks/interface/`.

## Structure

- **interface/**: on_tool_start.py, on_tool_exit.py
- **instance/**: Empty. Base instances would go here; currently all instances are tool-specific.

## Gotchas

- instance/ is empty; audit may flag tools that reference base events but have no base instances (that's expected).
- Engine checks base_iface_dir and base_inst_dir; both must exist as dirs for discovery (instance/ exists but is empty).
