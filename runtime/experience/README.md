# runtime/experience

Git-tracked institutional memory for the AI agent. Stores lessons learned, improvement suggestions, evolution history, and marketplace cache.

## Files

| File | Purpose |
|------|---------|
| `lessons.jsonl` | Recorded lessons from agent experience (one JSON object per line) |
| `suggestions.jsonl` | Generated improvement suggestions |
| `evolution.jsonl` | Applied evolution history (skill/rule changes) |
| `marketplace_cache.json` | Cached external marketplace data |

## Usage

Managed by `SKILLS` tool commands:
- `SKILLS learn "<text>"` — record a lesson
- `SKILLS analyze` — review lessons for patterns
- `SKILLS suggest` — generate improvement suggestions
- `SKILLS apply <id>` — apply a suggestion
- `SKILLS history` — view evolution history
