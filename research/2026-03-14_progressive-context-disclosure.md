# Progressive Context Disclosure & File System Paradigm

**Date**: 2026-03-14
**Source**: https://mp.weixin.qq.com/s/bbO9sIRUVag7iP56C9WiyA
**Projects**: claude-mem, OpenViking (Volcano Engine)

## Core Insights

### 1. Claude-mem: Progressive Context Disclosure (Single Agent)

**Problem**: Traditional agent frameworks dump entire conversation history + tool logs into every prompt. This creates:
- Rapidly growing token costs (tool outputs can be 5000+ tokens of noise)
- Signal-to-noise ratio drops below 5%
- Model hallucination increases with irrelevant context

**Solution: Three-Layer Retrieval**

| Layer | What | Token Cost | When |
|-------|------|------------|------|
| L0 | Compact index/directory of past actions | Minimal (~50 tokens per entry) | Always included |
| L1 | Timeline summaries | Medium (~200 tokens per entry) | When agent requests |
| L2 | Full details (specific tool output, code) | Full | Only by explicit ID lookup |

**Key mechanism**: "Read the table of contents, not the book." 90% of irrelevant context is filtered out.

**Lifecycle hooks**: Auto-captures 5 key events, runs background summarization into SQLite + vector DB.

### 2. OpenViking: File System Paradigm (Multi-Agent)

**Problem**: Multi-agent systems share context by passing full text → context overflow, memory pollution between agents.

**Solution: Tree-structured directory paradigm**

Instead of flat vector storage, all agent state is organized as a filesystem:
```
viking://resources/Agent_A_logs/
viking://memories/shared/project_context.md
viking://skills/code_review/
```

**Key principles**:
- **Pass pointers, not content**: Agents exchange directory paths or summary pointers, not full text
- **Physical isolation + logical sharing**: Private workspaces prevent cross-contamination
- **L0/L1/L2 graded loading**: Start with directory listing, drill into summaries, then full content
- **Observable traces**: Full audit trail of which agent read what from where

**Results**: Task completion 35.65% → 51-52%; Token cost -96%.

## Our Current State

### What we already have (partial alignment)

| Concept | Our Implementation | Gap |
|---------|-------------------|-----|
| File-based knowledge | `AGENT.md`, `skills/`, `memory/` | Already tree-structured |
| Agent state | `SessionContext` with full message history | No compression/summarization |
| Tool results | Full output passed back to LLM | No truncation/summarization |
| Context feeds | `_package_message()` packages CWD, file list | No progressive disclosure |
| Brain system | `brain/` with tasks, lessons | Basic, not integrated into context lifecycle |
| Compression | `needs_compression()` + `_compress_context()` | Exists but rarely triggers |

### Critical gaps

1. **No tool output summarization**: `exec`, `read_file`, `search` results pass full raw output to context. A `grep` returning 2000 chars of matches stays forever in context.

2. **No L0/L1/L2 loading**: Every message gets full context. There's no "summary first, detail on demand" pattern.

3. **No context pruning between rounds**: Tool results from round 1 still occupy context in round 10, even when no longer relevant.

4. **No session persistence**: Sessions are in-memory only. Server restart = all context lost.

## Migration Plan

### Phase 1: Tool Output Summarization (Immediate Impact)

**Where**: `_execute_tool_call()` result handling in `conversation.py`

**Approach**:
- After executing a tool, if the output exceeds a threshold (e.g., 500 chars), create a summary:
  - For `read_file`: Keep first/last 5 lines + total line count
  - For `exec`: Keep exit code + last 10 lines of output
  - For `search`: Keep match count + first 5 matches
- Store full output in a "detail store" keyed by tool_call_id
- Pass summary to context; full output retrievable if agent asks

### Phase 2: Progressive Context Compression (Medium-term)

**Where**: `SessionContext` + `_compress_context()`

**Approach**:
- After each round, summarize completed tool call results
- Older rounds get progressively more compressed
- Keep the "freshness window" (last 2-3 rounds) at full fidelity
- Rounds beyond the window → summarized to 1-2 sentences

### Phase 3: Session Persistence (Required for any long-term memory)

**Where**: New `SessionStore` class

**Approach**:
- Save sessions to `runtime/sessions/<session_id>.json`
- On server start, load existing sessions
- Auto-save after each round completes

### Phase 4: File System Paradigm Integration (Strategic)

**Where**: Brain system + context feeds

**Approach**:
- Organize agent knowledge as structured directories:
  ```
  runtime/brain/
    memory.md          # L0: always loaded
    tasks.json         # L0: active tasks
    lessons/           # L1: loaded on demand
    sessions/          # L2: loaded by specific session ID
  ```
- Context feed provides L0 (memory + active tasks) always
- Agent can request L1 (lessons relevant to current task) via tool
- Agent can request L2 (specific past session details) via tool

## Immediate Actions

1. **Truncate tool results in context** — cap at 500 chars for read/search, 300 for exec
2. **Add session persistence** — save/load from runtime/sessions/
3. **Implement L0 context header** — always include memory.md + active tasks
4. **Tool output store** — full results accessible by ID if agent needs them
