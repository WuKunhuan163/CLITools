# rag-20260316

Vector-enhanced brain using sentence embeddings for semantic retrieval. Built on the PlugMem concept: knowledge is not just stored, it's structured for retrieval.

## Philosophy

Text search finds what you remember. Semantic search finds what you need. This brain type adds vector embeddings to the knowledge and episodic tiers, enabling agents to find relevant past experience by meaning, not just keywords.

## Tiers

- **working**: Flatfile (same as clitools). Hot state doesn't benefit from embeddings.
- **knowledge**: Lessons stored as text + embedded vectors. `BRAIN recall "concept"` uses cosine similarity instead of substring match.
- **episodic**: MEMORY.md entries embedded for semantic retrieval of long-term facts.

## Dependencies

```bash
PYTHON pip install sentence-transformers faiss-cpu numpy
```

Embedding model: `all-MiniLM-L6-v2` (384 dimensions, ~80MB). Runs locally, no API calls.

## Key Differences from clitools

| Aspect | clitools | rag |
|--------|----------|-----|
| Recall search | Substring match | Cosine similarity (semantic) |
| Knowledge scaling | Linear scan (slow at 100+ lessons) | FAISS index (fast at 10K+ entries) |
| Dependencies | None | sentence-transformers, faiss-cpu, numpy |
| Storage overhead | Text only | Text + embeddings (~1.5KB per entry) |
| Cold start | Instant | ~5s (load embedding model) |

## When to Use

- Large knowledge bases (100+ lessons, 50+ memory entries)
- When keyword search misses conceptually related items
- When past discoveries need to be matched to current context automatically
- Research-heavy workflows where domain knowledge accumulates rapidly

## Status

Blueprint defined. Backend implementation (`logic/_/brain/backends/rag.py`) is planned. The FAISS index and embedding pipeline need to be built.

## Architecture

```
knowledge/
├── lessons.jsonl       # Raw lesson text (L2)
├── embeddings.npy      # Numpy array of lesson embeddings
├── faiss.index         # FAISS similarity index
└── metadata.json       # Maps index positions to lesson IDs
```

On `BRAIN recall "query"`:
1. Encode query with sentence-transformer
2. Search FAISS index for top-k similar entries
3. Retrieve full lessons from lessons.jsonl
4. Return ranked results with similarity scores
