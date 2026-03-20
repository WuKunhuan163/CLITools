# runtime/

Tracked runtime data — institutional memory that persists across sessions and is version-controlled (unlike `data/` which is gitignored transient data).

## Structure

- `_/` — Symmetric command runtime state
  - `eco/brain/` — Brain context, tasks, sessions, exports (via `BRAIN` CLI)
  - `eco/experience/` — Lessons, suggestions, evolution history (via `SKILLS learn`)
- `sessions/` — Tool session state
- `cache/` — Runtime cache

## Symmetric Root Directory

`runtime/` is a **symmetric root directory** — each tool can have its own `runtime/` for tracked runtime data specific to that tool. The project root's `runtime/` holds cross-tool data. The `_/` subdirectory follows the same convention as `logic/_/` — it contains data for symmetric CLI commands.

## Relationship to data/

| Aspect | `data/` | `runtime/` |
|--------|---------|------------|
| Git tracking | Ignored | Tracked |
| Content type | Caches, logs, session state | Institutional memory, evolution |
| Lifespan | Ephemeral, regenerable | Permanent, accumulative |
| Example | `data/log/`, `data/run/` | `runtime/_/eco/experience/lessons.jsonl` |
