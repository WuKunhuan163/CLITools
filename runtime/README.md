# runtime/

Tracked runtime data — institutional memory that persists across sessions and is version-controlled (unlike `data/` which is gitignored transient data).

## Structure

- `experience/` — Agent's cross-tool experience: lessons, suggestions, evolution history.
  - `lessons.jsonl` — Captured lessons from bug fixes and discoveries.
  - `suggestions.jsonl` — Generated improvement suggestions.
  - `evolution.jsonl` — Audit trail of applied changes.
  - `marketplace_cache.json` — Cached marketplace browse results.

## Symmetric Root Directory

`runtime/` is a **symmetric root directory** — each tool can have its own `runtime/` for tracked runtime data specific to that tool. The project root's `runtime/` holds cross-tool data.

## Relationship to data/

| Aspect | `data/` | `runtime/` |
|--------|---------|------------|
| Git tracking | Ignored | Tracked |
| Content type | Caches, logs, session state | Institutional memory, evolution |
| Lifespan | Ephemeral, regenerable | Permanent, accumulative |
| Example | `data/log/`, `data/run/` | `runtime/experience/lessons.jsonl` |
