# OpenClaw Context Engineering Analysis

**Date**: 2026-03-09
**Purpose**: Analyze OpenClaw's prompt architecture, nudge mechanisms, memory system, and context engineering for replication in AITerminalTools.

## 1. System Prompt Architecture

OpenClaw builds a custom system prompt per agent run with fixed sections:

| Section | Purpose | Replicable? |
|---------|---------|-------------|
| Reasoning | Thinking visibility toggle | Yes — via tier config |
| Runtime | Host, OS, model, repo root | Yes — `build_runtime_header()` |
| Heartbeats | Periodic auto-turns for liveness | Partially — useful for long sessions |
| Reply Tags | Provider-specific syntax hints | Yes — per-provider pipeline |
| Date & Time | User-local timezone | Yes — trivial |
| Sandbox | Sandbox state when enabled | Yes — `--ask`/`--plan` modes |
| Workspace Files | Injected bootstrap files | **Key feature to replicate** |
| Documentation | Local docs path | Yes — AGENT.md, README |
| Skills | Available skills list (compact) | Yes — already have skills system |
| Safety | Guardrail reminders | Yes — basic version exists |
| Tooling | Tool list + descriptions | Yes — BUILTIN_TOOL_DEFS |

### Prompt Modes (3 tiers, maps to our tier system)

| OpenClaw Mode | Our Equivalent | Content |
|---------------|---------------|---------|
| `none` | Tier 0 | Base identity only |
| `minimal` | Tier 1 | Omits skills, memory, heartbeats |
| `full` | Tier 2 | All sections |

### Bootstrap File Injection

OpenClaw injects workspace files automatically:

| File | Purpose | Our Equivalent |
|------|---------|---------------|
| `SOUL.md` | Agent personality, communication style | **New: experience/<brain>/SOUL.md** |
| `IDENTITY.md` | Agent name, role, goals | **New: experience/<brain>/IDENTITY.md** |
| `USER.md` | User preferences | **New: experience/<brain>/USER.md** |
| `MEMORY.md` | Long-term persistent facts | **New: experience/<brain>/MEMORY.md** |
| `memory/YYYY-MM-DD.md` | Daily working logs | **New: experience/<brain>/daily/** |
| `AGENTS.md` | Multi-agent configuration | `AGENT.md` (existing) |
| `TOOLS.md` | Available tools reference | `AGENT.md` (existing) |
| `BOOTSTRAP.md` | First-run guide | Not needed (skills handle this) |
| `HEARTBEAT.md` | Periodic task instructions | Future: scheduled agent tasks |

**Max per-file**: 20,000 chars. **Total cap**: 150,000 chars. Sub-agents only get `AGENTS.md` + `TOOLS.md`.

## 2. Memory System

### Four-Layer Stack

1. **Session Context** — Current conversation within context window
2. **Daily Notes** (`memory/YYYY-MM-DD.md`) — Append-only daily logs
3. **Long-term Memory** (`MEMORY.md`) — Curated, distilled knowledge
4. **Semantic Search** (`memory_search`) — Vector/BM25 hybrid over all memory files

### Automatic Memory Flush (Pre-Compaction)

When nearing context limits, OpenClaw fires a silent agentic turn:
- System prompt: "Session nearing compaction. Store durable memories now."
- User prompt: "Write any lasting notes to memory/YYYY-MM-DD.md; reply with NO_REPLY if nothing to store."
- Triggers at `contextWindow - reserveTokens - softThresholdTokens`

**Key insight**: The agent is *prompted* to write its own memories before context is lost. This is a trainable habit, not hard-coded behavior.

### Vector Memory Search

- BM25 + vector hybrid (weighted: 0.7 vector, 0.3 text)
- MMR re-ranking for diversity (reduces duplicate snippets)
- Temporal decay (half-life 30 days: recent notes rank higher)
- Embedding providers: Mistral, Voyage, Gemini, OpenAI, Ollama, local GGUF

## 3. SOUL.md Best Practices (for Brain Types)

A good SOUL.md contains:
1. **Personality Traits** — Specific behavioral descriptions, not vague adjectives
2. **Communication Style** — Response format, tone, length defaults
3. **Values** — What to optimize for (accuracy vs. speed, action vs. analysis)
4. **Expertise** — Confident areas vs. defer areas
5. **Situational Behavior** — Context-specific rules (brainstorming, writing, debugging)
6. **Anti-Patterns** — Explicit "never do this" list

**Key rule**: Every line should be specific enough to test. "Be concise" is useless; "Default to 2-3 sentences. If I need more, I'll ask." is testable.

## 4. Session Knowledge Transfer

OpenClaw supports:
- **Session Tools API**: `sessions_list`, `sessions_history`, `sessions_send`
- **Inter-session messages**: Tagged with `provenance.kind = "inter_session"`
- **Export/Import**: Full agent config as `.tar.gz` archive
- **Memory Pipeline Skill**: Extracts facts, builds knowledge graphs, generates briefings

## 5. Mechanisms to Replicate

### Priority 1: Bootstrap File Injection

Inject key files from `experience/<brain_type>/` into system prompt:
- `SOUL.md` → Agent personality
- `MEMORY.md` → Long-term facts
- `USER.md` → User preferences
- Daily notes → Recent context

### Priority 2: Memory Flush

Before session context exceeds a threshold, prompt the agent to write durable memories.

### Priority 3: Session Export/Import

Pack session state (environment, messages, memory) into a portable format.

### Priority 4: Semantic Memory Search

BM25 + vector hybrid search over memory files (can use TF-IDF as lightweight fallback).

## 6. Anti-Patterns from OpenClaw

- Default SOUL.md is useless ("be helpful, have opinions, be concise")
- Memory files grow unbounded without periodic pruning
- Sub-agents get minimal context (by design — reduces cost)
- Heartbeat can trigger unnecessary API calls
