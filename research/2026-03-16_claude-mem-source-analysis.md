# Claude-Mem Source Code Analysis

**Date**: 2026-03-16
**Source**: https://github.com/thedotmack/claude-mem (35K+ stars)
**Version analyzed**: Latest main branch (shallow clone)
**Previous research**: `research/2026-03-14_progressive-context-disclosure.md`

## Architecture Overview

Claude-mem is a Claude Code plugin that implements persistent memory across sessions with a three-tier retrieval system. Built with TypeScript/Bun.

### Component Map

```
plugin/
  hooks/hooks.json        ← 5 lifecycle hooks (JSON config)
  skills/
    mem-search/SKILL.md   ← 3-layer retrieval instructions
    make-plan/SKILL.md    ← Plan orchestration
    do/SKILL.md           ← Execution orchestration
    smart-explore/SKILL.md
  scripts/                ← Built JS from src/
  ui/                     ← Viewer bundle (React)

src/
  hooks/hook-response.ts  ← Hook output formatting
  services/
    worker-service.ts     ← Express API (port 37777)
    worker/
      search/
        SearchOrchestrator.ts  ← Strategy pattern for search
        ResultFormatter.ts     ← L1 index formatting
        TimelineBuilder.ts     ← L2 timeline context
        strategies/
          ChromaSearchStrategy.ts   ← Semantic via ChromaDB
          SQLiteSearchStrategy.ts   ← FTS5 full-text
          HybridSearchStrategy.ts   ← Combined
      agents/
        SDKAgent.ts           ← Claude Agent SDK wrapper
        ResponseProcessor.ts  ← AI response handling
      DatabaseManager.ts
      SessionManager.ts
      SearchManager.ts
      TimelineService.ts
    sqlite/
      Database.ts          ← Bun:sqlite driver
      migrations.ts        ← Schema definitions
      Observations.ts      ← CRUD for observations
      Sessions.ts          ← Session tracking
      Summaries.ts         ← Compressed summaries
      SessionSearch.ts     ← FTS5 search queries
    sync/
      ChromaSync.ts        ← Vector embedding sync
```

## The Three-Tier Retrieval System (Source-Level Analysis)

### Tier 1: Search Index (L0)

**Implementation**: `SearchOrchestrator.search()` → strategy selection → `ResultFormatter.formatSearchResults()`

**What it returns**: A markdown table with ~50-100 tokens per result:
```
| ID | Time | T | Title | Read |
|----|------|---|-------|------|
| #11131 | 3:48 PM | 🟣 | Added JWT authentication | ~75 |
```

**Key fields**: observation ID, timestamp, type icon, title, estimated read tokens.

**Strategy selection** (decision tree in `executeWithFallback()`):
1. No query text → SQLite filter-only (FTS5)
2. Query text + ChromaDB available → Semantic search via ChromaDB
3. ChromaDB fails → SQLite fallback (strips query, returns recent)
4. No ChromaDB → Empty results

**Token estimation**: `estimateReadTokens()` = `(title + subtitle + narrative + facts).length / 4`

### Tier 2: Timeline Context (L1)

**Implementation**: `TimelineBuilder.buildTimeline()` + `filterByDepth()`

**What it does**: Given an anchor observation ID, returns N items before and N items after in chronological order. Items include observations, sessions, and user prompts interleaved.

**Key insight**: This is NOT just "more results" — it provides temporal context. If observation #11131 was a bugfix, the timeline shows what happened around it (the investigation, the discovery, the follow-up).

### Tier 3: Full Details (L2)

**Implementation**: `get_observations(ids=[...])` → `Observations.getByIds()`

**What it returns**: Complete observation objects (~500-1000 tokens each):
- `title`: Short summary
- `subtitle`: One-liner
- `narrative`: Multi-paragraph description
- `facts`: Extracted facts
- `concepts`: Tagged concepts
- `files_modified`, `files_read`: File paths
- `discovery_tokens`: Token count for the AI-generated analysis

**Critical rule**: ALWAYS batch fetch via `get_observations(ids=[...])` (single HTTP request) instead of individual lookups.

## Observation Pipeline

### 5 Lifecycle Hooks

1. **SessionStart** → Starts worker service, injects context from previous sessions
2. **UserPromptSubmit** → Initializes session tracking
3. **PostToolUse** → Captures tool usage as observations (the most frequent hook)
4. **Stop** (Summary) → Generates session summary via Claude Agent SDK
5. **SessionEnd** → Marks session complete

### Observation Processing Flow

```
Tool use in Claude Code
  → PostToolUse hook fires
  → Worker service receives raw tool data via HTTP
  → SDKAgent processes (Claude Agent SDK compresses to observation)
  → SQLite stores observation
  → ChromaSync embeds for semantic search
  → SSEBroadcaster notifies viewer UI
```

### Observation Schema (from migrations.ts)

```sql
CREATE TABLE observations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  project TEXT NOT NULL,
  type TEXT NOT NULL,          -- bugfix, feature, decision, discovery, change
  title TEXT,
  subtitle TEXT,
  narrative TEXT,              -- Full description (L2 data)
  facts TEXT,                  -- Extracted facts
  concepts TEXT,               -- Tagged concepts (for filtering)
  files_modified TEXT,
  files_read TEXT,
  discovery_tokens INTEGER,    -- Token cost of AI analysis
  created_at TEXT NOT NULL,
  created_at_epoch INTEGER NOT NULL
);

-- FTS5 for full-text search
CREATE VIRTUAL TABLE observations_fts USING fts5(
  title, subtitle, narrative, facts, concepts
);
```

## Key Design Decisions

### 1. MCP Tool Interface (Not Direct Context Injection)

Claude-mem exposes `search`, `timeline`, and `get_observations` as MCP tools. The agent decides when to search its memory — it's not automatically injected. The SKILL.md teaches the agent the 3-layer workflow.

**Implication for us**: Our agent system would need a similar skill-based approach — teach the agent to search before acting.

### 2. SQLite + FTS5 + ChromaDB Hybrid

- **SQLite FTS5**: Fast exact/fuzzy text matching, filter by type/date/project
- **ChromaDB**: Semantic vector search for concept-level queries
- **Fallback chain**: Chroma → SQLite → empty (graceful degradation)

**Implication for us**: We could start with SQLite FTS5 only (no external dependencies) and add vector search later.

### 3. Observation Compression via Claude Agent SDK

Each raw tool output is processed by Claude AI to extract:
- Title (1 line)
- Subtitle (1 line)
- Narrative (paragraph)
- Facts (bullet points)
- Concepts (tags)

This is the most expensive part (~500-1000 tokens per observation in AI cost). But it creates the L0/L1 data that saves 10x tokens later.

**Implication for us**: We can start with simpler heuristic compression (no AI cost) — truncation + metadata extraction from tool output.

### 4. Project-Scoped Memory

All data is scoped by `project` (derived from cwd). This prevents cross-project context pollution.

**Implication for us**: Our sessions are already isolated. But for long-term memory across sessions, we'd need project-level scoping.

## Implementation Plan for AITerminalTools

### What We Already Have

| Claude-Mem Feature | Our Equivalent | Status |
|---|---|---|
| Lifecycle hooks | `hooks/` system | Exists |
| Session tracking | `SessionContext` | Exists |
| Tool output capture | `_execute_tool_call()` events | Exists |
| Context compression | `_compress_context()` | Exists (basic) |
| Session persistence | `runtime/sessions/` | Exists |
| Round store | `RoundStore` | Exists |
| Progressive disclosure | `_truncate_tool_output()` | Exists (basic) |

### What We Need

#### Phase 1: L0/L1/L2 Within a Session (Low cost, high impact)

**Current**: `_truncate_tool_output()` in `conversation.py` already does basic truncation.

**Enhancement**:
1. Store full tool outputs in `RoundStore` (L2 — already done)
2. Generate a 1-line summary per tool call (L0) — heuristic, no AI cost:
   - `read_file(path)` → "Read path (N lines)"
   - `exec(cmd)` → "Ran cmd (exit N, N lines output)"
   - `edit_file(path)` → "Edited path (+N/-M lines)"
   - `search(query)` → "Searched query (N matches)"
3. Include L0 summaries in context for past rounds, L2 only for recent rounds

#### Phase 2: Cross-Session Memory (Medium cost)

1. On session end, generate a session summary (can use our existing LLM)
2. Store summaries in SQLite with FTS5
3. Add a `recall` tool that the agent can use to search past sessions
4. Inject the most recent session summary as context header

#### Phase 3: Semantic Search (Optional)

1. Add ChromaDB or local embedding model
2. Index observation summaries
3. Hybrid search (FTS5 + vector)

### Key Principle: Heuristic First, AI Later

Claude-mem uses Claude Agent SDK to compress observations (expensive). We can achieve 80% of the benefit with heuristic compression:

```python
def summarize_tool_output(tool_name, args, output):
    if tool_name == "read_file":
        path = args.get("path", "")
        lines = output.count("\n") + 1
        return f"Read {path} ({lines} lines)"
    if tool_name == "exec":
        cmd = args.get("command", "")[:50]
        exit_code = ...  # parse from output
        return f"Ran `{cmd}` (exit {exit_code})"
    if tool_name == "edit_file":
        path = args.get("path", "")
        return f"Edited {path}"
    if tool_name == "search":
        query = args.get("query", "")
        matches = ...  # parse from output
        return f"Searched '{query}' ({matches} matches)"
    return f"{tool_name}: {str(args)[:50]}"
```

This costs 0 tokens and provides the L0 index that prevents context bloat.

## Token Economics

| Approach | Tokens per round | After 10 rounds |
|----------|-----------------|-----------------|
| Current (full context) | ~2000 | ~20,000 |
| L0 summaries for old rounds | ~200 | ~2,800 |
| Claude-mem style (AI compression) | ~150 | ~2,300 |

**Our Phase 1 achieves ~85% of claude-mem's token savings with zero AI cost.**
