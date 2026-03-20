# logic/search/ — Knowledge Search

Provides semantic and keyword search across tools, skills, lessons, and documentation.

## Key Files

| File | Purpose |
|------|---------|
| `knowledge.py` | TF-IDF index for searching docs, lessons, skills |
| `semantic.py` | Semantic search utilities |
| `tools.py` | Tool search and discovery helpers |

## CLI

```bash
TOOL --search all "query"       # Search everything (tools, skills, lessons, docs)
TOOL --search skills "topic"    # Search skills by topic
TOOL --search docs "topic"      # Search documentation
BRAIN recall "keyword"          # Search brain (lessons, activity, context)
```

## For Agents

Always use `TOOL --search all "query"` before implementing anything. This is the most important habit for avoiding duplicate implementations.
