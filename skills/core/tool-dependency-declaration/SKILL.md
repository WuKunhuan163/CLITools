---
name: tool-dependency-declaration
description: Declaring tool dependencies in tool.json when importing from other tools' interfaces. Ensures setup.py installs prerequisites automatically.
---

# Tool Dependency Declaration

## Principle

**If you call it, declare it.** When a tool imports from another tool's `interface/main.py`, the calling tool must declare the dependency in its `tool.json`. This ensures `setup.py` installs prerequisites automatically and prevents import failures on fresh installations.

## When This Applies

| Import Pattern | Needs Declaration? |
|---|---|
| `from tool.LLM.interface.main import send` | Yes — `"LLM"` in `dependencies` |
| `from logic.agent.ecosystem import ...` | No — `logic/` is shared framework |
| `from interface.utils import retry` | No — `interface/` is facade layer |
| `from tool.GIT.interface.main import ...` | Yes — `"GIT"` in `dependencies` |

## How to Declare

In the calling tool's `tool.json`:

```json
{
  "name": "MY_TOOL",
  "dependencies": ["LLM", "GIT"],
  "pip_dependencies": ["requests"]
}
```

- `dependencies` — other tools (installed recursively via `setup.py`)
- `pip_dependencies` — Python packages (installed via pip)
- `pip_dependencies_optional` — Python packages that are nice to have (skipped on failure)

## Root tool.json

The project root `tool.json` has two separate fields:

```json
{
  "tool_dependencies": ["PYTHON", "GIT", "SKILLS"],
  "tools": ["PYTHON", "GIT", "LLM", ...]
}
```

- `tool_dependencies` — tools installed during `setup.py`
- `tools` — complete registry of available tools

If root-level code (like `hooks/instance/AI-IDE/Cursor/brain_inject.py`) imports from `logic/`, no tool dependency is needed since `logic/` is framework-level. If it imports from `tool/LLM/interface/`, then `LLM` must be added to `tool_dependencies`.

## Detection Checklist

When creating or modifying a tool:

1. Search all `from tool.XXX.` imports in your code
2. For each unique `XXX`, verify it's in your `tool.json` `dependencies` list
3. If missing, add it
4. Run `TOOL --audit imports` to check for undeclared dependencies

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Import from `tool.LLM.logic.brain` directly | Import from `tool.LLM.interface.main` instead (facade layer) |
| Forget to declare after adding an import | Run `TOOL --audit imports` before committing |
| Declare `logic/` as a dependency | `logic/` is framework-level, no declaration needed |
| Import at module level causing circular deps | Use lazy imports inside functions |

## Relationship to Other Skills

- `tool-json-specification` — full spec for tool.json fields
- `code-quality-review` — IMP001-IMP005 import rules, includes undeclared dependency detection
- `tool-interface` — how to create and use `interface/main.py` properly
