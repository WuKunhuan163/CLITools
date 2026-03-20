# Evolution System Implementation Plan

## Design Principle

We do NOT need to replicate OpenClaw's file-as-brain architecture verbatim. Cursor already provides context injection via `.cursor/rules/`, `for_agent.md`, and skills. Our approach: **build the introspection and evolution loop as tools, leveraging our existing infrastructure**.

## Architecture

```
tool/SKILLS/                        runtime/experience/
├── main.py       (CLI entry)       ├── lessons.jsonl      (captured lessons)
└── logic/                          ├── suggestions.jsonl  (generated suggestions)
    └── evolution.py (brain logic)  └── evolution.jsonl    (applied changes history)
```

The `runtime/` directory is a **symmetric root directory** — each tool (including the project root) has its own `runtime/` for tracked runtime data. `runtime/experience/` at the project root holds the agent's cross-tool institutional memory.

Data flow:

```
Agent Transcripts (agent-transcripts/*.jsonl)
    + Session Logs (tool/*/data/logs/)
    + Lessons (runtime/experience/lessons.jsonl)
        |
        v
    SKILLS analyze  (pattern recognition)
        |
        v
    SKILLS suggest  (typed, scored suggestions)
        |
        v
    SKILLS apply    (human-gated, with action guide)
        |
        v
    SKILLS history  (evolution audit trail)
```

## Mapping to Our Infrastructure

### Brain Files (already covered)

| Function | Our Implementation |
|----------|-------------------|
| Agent identity | `.cursor/rules/AITerminalTools.mdc` (always loaded) |
| Workspace conventions | `for_agent.md` (always loaded) |
| Tool-specific knowledge | `tool/<NAME>/for_agent.md` |
| Institutional memory | `runtime/experience/lessons.jsonl` |
| Session raw data | `agent-transcripts/*.jsonl` |
| Curated skills | `skills/core/*/SKILL.md` |
| Enforcement | `tool/<NAME>/hooks/pre_commit.py` |
| Improvement suggestions | `runtime/experience/suggestions.jsonl` |
| Evolution audit trail | `runtime/experience/evolution.jsonl` |

### Data vs Logic Separation

Following AITerminalTools convention:
- **`runtime/experience/`**: Runtime data produced by the agent during operation (lessons, suggestions, evolution history). Tracked by Git as a symmetric root directory.
- **`tool/SKILLS/logic/evolution.py`**: The brain system implementation — analysis algorithms, suggestion generation, pattern matching. Pure functions that operate on brain data.

### Symmetric Root Directory: `runtime/`

`runtime/` is a new symmetric root directory, meaning each tool (including the project root) can have its own `runtime/` for tracked runtime artifacts. Unlike `data/` (gitignored transient data), `runtime/` is version-controlled institutional memory. The `experience/` subdirectory holds the evolution system's brain data.

### Evolution Commands (implemented)

All implemented as subcommands of the existing `SKILLS` tool:

#### `SKILLS learn "<lesson>" [--tool NAME] [--severity info|warning|critical]`
- Records a lesson to `data/brain/lessons.jsonl`
- Delegates to `logic/evolution.record_lesson()`

#### `SKILLS lessons [--last N] [--tool NAME]`
- Displays recent lessons with filtering

#### `SKILLS analyze [--days N] [--tool NAME]`
- Reads `lessons.jsonl` entries from the last N days
- Groups by tool, severity, and keyword clusters
- Identifies patterns: repeated tool names, escalating severity, similar contexts
- Delegates to `logic/evolution.analyze()` which returns a structured dict
- Outputs formatted summary

#### `SKILLS suggest [--focus security|performance|quality]`
- Based on analysis, generates typed suggestions:
  - `rule`: Propose a new `for_agent.md` entry
  - `hook`: Propose a new pre-commit check
  - `skill`: Propose a new skill document
- Each suggestion has: id, type, confidence (0-1), content, evidence
- Delegates to `logic/evolution.suggest()`
- Writes to `data/brain/suggestions.jsonl`

#### `SKILLS apply <suggestion-id>`
- Reads the suggestion from `suggestions.jsonl`
- Displays full details and a concrete **Action Guide** with step-by-step instructions
- Records the action to `data/brain/evolution.jsonl`
- Delegates to `logic/evolution.apply_suggestion()`

#### `SKILLS history [--last N]`
- Shows the evolution audit trail from `evolution.jsonl`

## What We Explicitly Don't Need

- `SOUL.md`: `.cursor/rules/AITerminalTools.mdc` already serves this purpose
- `MEMORY.md`: Our skills + lessons system is better structured
- Heartbeat/cron: Cursor is interactive; the agent runs on demand
- Daily logs: Agent transcripts already capture this
- Channel system: Not applicable (single IDE context)
