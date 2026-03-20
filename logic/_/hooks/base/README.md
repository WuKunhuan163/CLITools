# Hooks Base

Framework-level hook interfaces and instances. Shared across all tools.

## Purpose

Provides the canonical set of hook events (on_tool_start, on_tool_exit) and optional base instances. Tool-specific hooks live in `<TOOL>/hooks/`.

## Structure

| Path | Content |
|------|---------|
| interface/ | OnToolStart, OnToolExit |
| instance/ | (empty; tool-specific instances go in tool's hooks/instance/) |

## Key Exports

Interfaces are discovered by HooksEngine from this directory; no explicit exports. See interface/README.md for event definitions.
