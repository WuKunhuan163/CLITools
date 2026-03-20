# claude-mem-20260316

Context-compression brain inspired by [claude-mem](https://github.com/anthropics/claude-mem)'s three-layer retrieval workflow. Optimized for token efficiency.

## Philosophy

"More memory can make agents less effective." This brain type prioritizes compact, retrievable knowledge over raw storage. Every piece of data has three representations:

- **L0** (one-line summary): Always in context. ~10 tokens per item.
- **L1** (paragraph summary): Retrieved on match. ~100 tokens per item.
- **L2** (full content): Retrieved on explicit request. Variable size.

## Tiers

- **working**: Same as clitools, plus `tool_outputs/` directory for L2 retention of raw tool outputs. Context window uses freshness_window=6 for L0 compression.
- **knowledge**: lessons.jsonl (L2) + summaries.jsonl (L0/L1 index). Retrieval starts at L0, expands to L1 on keyword match, L2 on explicit request.
- **episodic**: daily_summaries.jsonl auto-compresses daily logs into one-line entries.

## Key Differences from clitools

| Aspect | clitools | claude-mem |
|--------|----------|------------|
| Context strategy | FIFO drop | L0 compress, then FIFO |
| Tool output retention | Discarded after context | Stored in L2 for retrieval |
| Knowledge retrieval | Linear scan | L0 → L1 → L2 progressive |
| Daily logs | Raw | Auto-summarized |

## When to Use

- Long sessions with many tool calls (context pressure)
- Large knowledge bases (50+ lessons)
- When token cost optimization is critical
- When past tool outputs need to be retrievable later in the session

## Status

Partially implemented. L0 summaries in `conversation.py` and `session_context.py` are active. L2 store and progressive retrieval for knowledge tier are planned.

## Reference

See `research/2026-03-16_claude-mem-source-analysis.md` for the full architecture analysis.
