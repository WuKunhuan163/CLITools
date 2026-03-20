# Agent Architecture Research: Turning Model Providers into Agents

**Date**: 2026-03-09
**Goal**: Design a `--agent` mode that gives any tool autonomous agent capabilities, using any LLM model provider as the brain.

## 1. How AI IDEs Implement Agent Mode

### Cursor
- **Context injection**: Silently attaches open files, git status, OS info, workspace rules before every message
- **AST-based refactoring** for mechanically sound code edits
- **Sub-agent spawning** for independent child tasks
- **Context compression**: When window fills, summarizes older messages transparently
- **Agent loop**: user input → context injection → model → tool execution → response → repeat

### GitHub Copilot
- **Multi-model**: GPT-4 plans, speculative decoder applies changes
- **Cycle**: analyze → execute → verify → iterate until done
- **Dual efficiency**: large model generates plan, small model applies

### Windsurf (Cascade)
- **Automatic context assembly**: Figures out relevant context with minimal setup
- **Cascade agent** automatically gathers what it needs

### Claude Code
- **Hooks/worktrees** for context management
- **YOLO mode**: Auto-run safe commands (tests, builds, lint) without approval

### Common Pattern
All IDEs follow: **user prompt → context enrichment → LLM call → tool execution → state feedback → next iteration**

## 2. Open-Source Agent Frameworks

### acpx (Agent Client Protocol CLI)
- Headless CLI client for agent-to-agent communication
- "One-shot mode" via `exec` for stateless tasks
- Protocol-based communication (not PTY scraping)
- Prompt queueing, cooperative cancellation

### llcat ("cURL for LLMs")
- Stateless, transparent CLI tool
- OpenAI-compatible `/chat/completions` caller
- Tool calling via OpenAI spec + MCP STDIO servers
- No state between runs — closest to our `--agent feed` concept

### Gemini CLI
- Built-in tools: search, file ops, shell commands
- MCP support for custom integrations
- 96K+ stars — most popular agent CLI

### Timbal
- Python framework for Agents + Workflows
- Async concurrent tool execution
- Automatic tool schema generation
- Multi-provider LLM routing

## 3. Design for AITerminalTools `--agent`

### Core Concept

Every tool gets `--agent` as a symmetric command that turns it into an autonomous workspace. The agent operates within the tool's directory as its codebase root.

### Three-Tier Assistance Levels

| Tier | Name | Feed Content | Use Case |
|------|------|-------------|----------|
| 0 | **Minimal** | Command output only | AI IDE (Cursor) that provides its own context |
| 1 | **Standard** | Output + file listing + error context + tool hints | Standard LLM API integration |
| 2 | **Full** | Everything in T1 + skills injection + quality checks + nudges + state awareness | Standalone agent (no external IDE) |

Each tool has an `agent/` directory in its logic that can override/extend behaviors per tier.

### Command Protocol

```bash
# Start agent session (boots local server, returns session_id)
<TOOL> --agent prompt "Build a todo app with dark mode"

# Feed next action / get state (stateless call)
<TOOL> --agent feed <SESSION_ID> <COMMAND>

# Monitor session
<TOOL> --agent status <SESSION_ID>

# Configure API keys
<TOOL> --agent setup

# List active sessions
<TOOL> --agent sessions
```

### Architecture

```
logic/agent/                          # Root agent infrastructure
├── __init__.py
├── loop.py                           # Core agent loop (prompt → LLM → tools → feedback)
├── context.py                        # Context builder (tiers 0/1/2)
├── tools.py                          # Tool schema builder for LLM
├── state.py                          # Session state management
├── nudge.py                          # Nudge/quality detection (extracted from conversation.py)
├── quality.py                        # Write quality checks (extracted from conversation.py)
└── feed.py                           # Feed protocol (text + tool separation)

tool/<NAME>/logic/agent/              # Per-tool agent extensions (optional)
├── __init__.py
├── skills.py                         # Tool-specific skills/hints for agent
└── handlers.py                       # Tool-specific tool handlers

interface/agent.py                    # Public facade
```

### Feed Protocol

The `--agent feed` command returns structured JSON:
```json
{
  "type": "state",
  "session_id": "abc123",
  "status": "running",
  "cwd": "/Applications/AITerminalTools/tool/BILIBILI",
  "last_action": {"tool": "exec", "command": "...", "ok": true, "output": "..."},
  "environment": {"files": [...], "errors": [...], "tools": [...]},
  "nudge": null,
  "tier": 1
}
```

### Integration Points

- **Cursor/VS Code**: Use Tier 0. Agent drives via `--agent feed`, IDE provides its own context
- **LLM HTML GUI**: Use Tier 2. Full autonomous operation with quality checks and nudges
- **CLI/API**: Use Tier 1. Balanced context for programmatic access

### Key Design Decisions

1. **Stateless feed**: Each `--agent feed` call is self-contained — no long-running server needed for basic operation
2. **Session persistence**: State saved to `data/session/` for crash recovery
3. **Provider-agnostic**: Any registered LLM provider can drive the agent loop
4. **Extensible per-tool**: Each tool can add custom skills, handlers, and quality checks
5. **Tier-based**: Platform determines how much context to inject (AI IDEs need less)

## 4. Migration Path from LLM Tool

Currently, `tool/LLM/logic/task/agent/conversation.py` contains:
- `AgentEnvironment` → move to `logic/agent/state.py`
- `build_runtime_state()` → move to `logic/agent/context.py`
- `ConversationManager` core loop → move to `logic/agent/loop.py`
- `_check_write_quality` → move to `logic/agent/quality.py`
- `_should_nudge` → move to `logic/agent/nudge.py`
- `BUILTIN_TOOLS` → move to `logic/agent/tools.py`
- Tool handlers (`_handle_exec`, etc.) → move to `logic/agent/tools.py`

What remains in `tool/LLM/`:
- Provider management (registry, config, rate limiting)
- Provider-specific pipelines
- Brain/memory system
- HTML GUI rendering
