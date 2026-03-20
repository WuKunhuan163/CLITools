# Workspace — Agent Self-Reflection

## Purpose

This file is a **stable reflection guide** for agents working on Workspace. It prompts self-evaluation and identifies improvement opportunities. It is NOT a recording file — session discoveries go to `BRAIN log` / `SKILLS learn`, not here.

## How to Update This File

This file should be **refined, not grown**:
- **Fix a gap** → remove it from "Known Gaps" and briefly note what replaced it
- **Discover a gap** → add it, but keep to 3-5 gaps
- **Session-specific notes** → `BRAIN log`, `SKILLS learn`, `runtime/experience/lessons.jsonl`
- **Never add a changelog or session log** — that belongs in git history and brain context

## Scope

This is a **logic-level** reflection file. Update it when you discover gaps or patterns specific to the  module. For cross-tool, ecosystem-level gaps, update the root  instead.

## Self-Check (after each task on this module)

- **Discovery**: Did I read this module's `for_agent.md` and search for related skills before coding?
- **Interface**: If I added reusable functionality, did I expose it in `interface/`?
- **Testing**: Did I run existing tests and add new ones for my changes?
- **Documentation**: Did I update `README.md` and `for_agent.md` to reflect my changes?

## Known Gaps

(Record module-specific improvement opportunities here. When fixed, remove and note the replacement.)

## Design Notes

(Stable, non-obvious architectural decisions or constraints. NOT per-session observations — only enduring design patterns.)
