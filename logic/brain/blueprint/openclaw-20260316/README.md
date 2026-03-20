# openclaw-20260316

OpenClaw-inspired brain blueprint for AITerminalTools.

## Philosophy

Adapted from [OpenClaw's memory architecture](https://github.com/openclaw/openclaw) (v2026.3.13) with key principles:

1. **Markdown is canonical** — All memory stored as plain text files. The index (SQLite/embeddings) is derived, files are source of truth. Debug by reading, not querying.

2. **Hybrid search (union, not intersection)** — Combines vector similarity (70%) with BM25 keyword matching (30%). Results from *either* method contribute. Exact matches and semantic matches both surface.

3. **Pre-compaction memory flush** — Before context overflow, the agent is prompted to save important memories. Prevents information loss during inevitable context compaction.

4. **Graceful degradation** — If embeddings fail, keyword search works. If keyword search fails, vector search works. If both fail, Markdown files remain.

5. **Self-improvement feedback loop** — Captures failures, corrections, and discoveries. Detects patterns (3+ similar events). Proposes improvements for human review.

## Differences from OpenClaw

| Aspect | OpenClaw | This Blueprint |
|--------|----------|---------------|
| Runtime | 24/7 Node.js daemon | On-demand IDE sessions |
| Storage | `~/.openclaw/memory/` | `runtime/_/eco/brain/sessions/<name>/` |
| Search | SQLite FTS5 + embeddings | Flatfile default, hybrid optional |
| Channels | WhatsApp, Telegram, etc. | IDE (Cursor, Claude Code) |
| Skills | External skill packages | Integrated SKILLS tool |
| Self-improvement | GitHub PR proposals | SKILLS learn → create → TOOL dev |

## Tiers

### Working
Hot state: context, tasks, activity, and curated memory (MEMORY.md). Injected at session start.

### Knowledge
Persistent lessons, learnings, errors, feature requests. Hybrid search with configurable weights. Chunking with 80-token overlap preserves cross-boundary context.

### Episodic
Long-term personality, accumulated memory, daily logs. Ebbinghaus-inspired decay deprioritizes old memories but never deletes them. High-value categories (preferences, contacts) are exempt from decay.

## Key Features

- **Curated Memory (MEMORY.md)**: Stable facts, preferences, decisions — always injected
- **Daily Logs**: Append-only session logs in `episodic/daily/YYYY-MM-DD.md`
- **Memory Categories**: preferences, contacts, projects, learnings, tools, custom
- **Pre-compaction Flush**: 4000-token buffer before hard limit triggers save prompt
- **Confidence Thresholds**: Learnings need 3+ occurrences at 0.9+ confidence to become skills
- **Pattern Detection**: Threshold of 3 similar failures triggers improvement proposal

## Usage

```bash
BRAIN session create my-brain --type openclaw-20260316
```

## Upgrade Path

The blueprint works with the `flatfile` backend out of the box. For full hybrid search:

1. Install dependencies: `pip install sentence-transformers faiss-cpu numpy`
2. Register a `hybrid` backend in `logic/brain/loader.py`
3. Update the knowledge tier to use `"backend": "hybrid"`
