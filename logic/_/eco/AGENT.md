# Ecosystem Navigation (`logic/eco/`)

## Purpose

Unified CLI for exploring the AITerminalTools ecosystem. Consolidates scattered discovery commands (TOOL --search, SKILLS show, BRAIN recall) into a single `TOOL --eco` entry point.

## Architecture

- `logic/eco/navigation.py` — Core navigation logic (dashboard, tool info, skill lookup, map, context, blueprint commands)
- `interface/eco.py` — Public facade (import from here)
- `bin/TOOL` `--eco` handler — CLI integration (display formatting)

## Key Commands

```
TOOL --eco                     Dashboard (tools, skills, brain, shortcuts)
TOOL --eco search "query"      Unified semantic search
TOOL --eco tool <name>         Tool deep-dive (docs, interface, tests)
TOOL --eco skill <name>        Load skill content
TOOL --eco map                 Directory structure
TOOL --eco here [cwd]          Context-aware navigation
TOOL --eco guide               Onboarding guide
TOOL --eco recall "query"      Brain memory search
TOOL --eco cmds                Blueprint shortcut commands
TOOL --eco cmd <name>          Run a shortcut
```

## Blueprint Commands

Brain blueprints (`data/_/runtime/_/eco/brain/blueprint.json` or `logic/_/brain/blueprint/<type>/blueprint.json`) can define custom commands:

```json
{
  "commands": {
    "audit": {
      "description": "Full code quality audit",
      "run": "TOOL --audit code && TOOL --audit imports"
    }
  }
}
```

These are accessible via `TOOL --eco cmds` / `TOOL --eco cmd <name>`.

## Design Decisions

- `TOOL --eco search` wraps `interface/search.py` — no duplicate implementation
- `TOOL --eco skill` searches all skill directories including tool-specific ones and symlinks
- Blueprint commands merge: parent type commands + runtime blueprint commands (runtime wins on conflict)
- `TOOL --eco here` detects hierarchy level from CWD (root, tool, module, skills, brain) and suggests relevant actions
