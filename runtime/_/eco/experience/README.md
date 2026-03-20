# runtime/_/eco/experience

Git-tracked institutional memory for AI agents. Contains two subsystems:

## 1. Brain Types (Agent Personality & Memory)

Each brain type is a named directory defining agent personality, expertise, and accumulated memory:

```
runtime/_/eco/experience/<brain_type>/
    SOUL.md        — Agent personality, communication style, values
    IDENTITY.md    — Agent name, role, goals
    USER.md        — User preferences
    MEMORY.md      — Long-term persistent facts (accumulated via write_memory)
    daily/         — Daily working logs (YYYY-MM-DD.md via write_daily)
```

**Why `<brain_type>/<session_id>/` not `<session_id>/<brain_type>/`?**

Brain-first hierarchy is correct because:
- Brain personality (SOUL.md) is **shared** across all sessions of that type
- Memory (MEMORY.md) **accumulates** across sessions — it's the brain's long-term store
- Sessions are **ephemeral instances** within a persistent brain
- Export/import transfers brain + session together as a unit
- Session state lives separately in `data/session/<id>.json`

Manage brains: `TOOL_NAME --agent brain [list|init <name>|show <name>]`

## 2. Lessons & Evolution (SKILLS integration)

| File | Purpose |
|------|---------|
| `lessons.jsonl` | Recorded lessons from agent experience (one JSON object per line) |
| `suggestions.jsonl` | Generated improvement suggestions |
| `evolution.jsonl` | Applied evolution history (skill/rule changes) |
| `marketplace_cache.json` | Cached external marketplace data |

Managed by `SKILLS` tool:
- `SKILLS learn "<text>"` — record a lesson
- `SKILLS analyze` — review lessons for patterns
- `SKILLS suggest` — generate improvement suggestions
- `SKILLS apply <id>` — apply a suggestion
- `SKILLS history` — view evolution history
