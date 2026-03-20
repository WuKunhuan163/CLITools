# CLIANYTHING — Agent Self-Reflection

## Purpose

This file is a **stable reflection guide** for agents working on CLIANYTHING. It prompts self-evaluation and identifies tool-specific improvement opportunities. It is NOT a recording file — session discoveries go to `BRAIN log` / `SKILLS learn`, not here.

## How to Update This File

This file should be **refined, not grown**:
- **Fix a gap** → remove it from "Known Gaps" and briefly note what replaced it
- **Discover a tool-level gap** → add it, but keep to 3-5 gaps
- **Session-specific notes** → `BRAIN log`, `SKILLS learn`, `runtime/experience/lessons.jsonl`
- **Never add a changelog or session log** — that belongs in git history and brain context

## Self-Check (after each task on this tool)

- **Discovery**: Did I read this tool's `for_agent.md` and search for related skills before coding?
- **Interface**: If I added reusable functionality, did I expose it in `interface/main.py`?
- **Testing**: Did I run existing tests and add new ones for my changes?
- **Documentation**: Did I update `README.md` and `for_agent.md` to reflect my changes?

## Known Gaps

(Tool-specific improvement opportunities. Keep to 3-5 items. Remove when fixed.)

## Design Notes

(Stable, non-obvious architectural decisions or constraints that affect how agents should work with this tool. NOT per-session observations — only enduring design patterns.)
