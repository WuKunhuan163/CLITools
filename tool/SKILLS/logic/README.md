# SKILLS Logic

Agent skill management — evolution system and marketplace. Provides the self-improvement loop (learn, analyze, suggest, apply) and external skill marketplace integration.

## Structure

| Module | Purpose |
|--------|---------|
| `evolution.py` | Brain/evolution system — lessons, analysis, suggestions, history |
| `marketplace.py` | External skill marketplace — browse, search, install from ClawHub |

## Data Storage

Brain data is stored in `runtime/_/eco/experience/`:
- `lessons.jsonl` — recorded lessons
- `suggestions.jsonl` — generated improvement suggestions
- `evolution.jsonl` — applied evolution history
- `marketplace_cache.json` — cached marketplace data
