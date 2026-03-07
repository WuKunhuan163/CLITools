# OpenClaw Source Code Analysis

Date: 2026-03-06  
Source: `tmp/openclaw/` (cloned from https://github.com/openclaw/openclaw)

---

## Q1: How Does OpenClaw Construct "Packaged State"?

OpenClaw's state packaging is NOT raw file dumps. It's a carefully structured system prompt with hierarchical context layers.

### Architecture: `src/agents/system-prompt.ts` → `buildAgentSystemPrompt()`

The system prompt is constructed from these sections, in order:

| # | Section | Source | Purpose |
|---|---------|--------|---------|
| 1 | Identity | Hardcoded | "You are a personal assistant running inside OpenClaw." |
| 2 | Tooling | `toolNames` + `toolSummaries` | List of available tools with 1-line descriptions |
| 3 | Tool Call Style | Hardcoded | "Default: do not narrate routine, low-risk tool calls" |
| 4 | Safety | Hardcoded | No independent goals, prioritize human oversight |
| 5 | CLI Reference | Hardcoded | Quick ref for OpenClaw subcommands |
| 6 | **Skills (mandatory)** | `skillsPrompt` from `workspace.ts` | **Forces agent to scan before every reply** |
| 7 | **Memory Recall** | `memory_search` tool availability | "Before answering about prior work: run memory_search" |
| 8 | Self-Update | `gateway` tool availability | Config changes require user approval |
| 9 | Model Aliases | `modelAliasLines` | Prefer aliases for model overrides |
| 10 | Workspace | `workspaceDir` + `workspaceNotes` | Working directory + dynamic notes |
| 11 | Docs | `docsPath` | Local docs + mirror URLs |
| 12 | Sandbox | `sandboxInfo` | Docker execution boundaries |
| 13 | User Identity | `ownerNumbers` | Authorized senders (hashed or raw) |
| 14 | Time | `userTimezone` | Current timezone |
| 15 | **Workspace Files (injected)** | `contextFiles` | **AGENTS.md, SOUL.md, TOOLS.md, etc.** |
| 16 | Silent Replies | Hardcoded | `<<SILENT>>` token for no-output responses |
| 17 | Heartbeat | `heartbeatPrompt` | Periodic self-check protocol |
| 18 | Runtime | `runtimeInfo` | agent, host, OS, model, shell, channel |

### Bootstrap Files (Context Injection)

OpenClaw loads these files from `~/.openclaw/workspace/` and embeds them:

```
AGENTS.md   - Agent rules, workspace conventions (like our for_agent.md)
SOUL.md     - Personality, tone, communication style
TOOLS.md    - User-facing tool usage guidance
IDENTITY.md - Agent name/identity
USER.md     - Info about the user
HEARTBEAT.md - Heartbeat configuration
BOOTSTRAP.md - General bootstrap context
MEMORY.md    - Memory for recall
```

Source: `src/agents/workspace.ts` → `loadWorkspaceBootstrapFiles()`

These files are:
1. Loaded from workspace directory
2. Filtered by session (some are session-specific)
3. Front-matter stripped
4. Size-capped (2MB per file)
5. Boundary-safe (can't escape workspace root via symlinks)
6. **Embedded directly into system prompt under `# Project Context`**

Key implementation: `src/agents/bootstrap-files.ts` → `resolveBootstrapContextForRun()`

### Skills Loading

Skills come from multiple sources with precedence:

```
Extra dirs (plugins) < Bundled < Managed < Personal < Project < Workspace
```

Source: `src/agents/skills/workspace.ts` → `loadSkillEntries()`

Skills are:
1. Scanned from `skills/*/SKILL.md`  
2. Front-matter parsed for metadata (emoji, env requirements, invocation policy)
3. Filtered by config and eligibility
4. Formatted into prompt with name + description + location
5. Path-compacted (`~/.bun/...` → `~/...`) to save tokens
6. Capped: max 150 skills, max 30,000 chars in prompt

The system prompt forces mandatory skill scanning:
```
## Skills (mandatory)
Before replying: scan <available_skills> <description> entries.
- If exactly one skill clearly applies: read its SKILL.md at <location> with `read`, then follow it.
- If multiple could apply: choose the most specific one, then read/follow it.
- If none clearly apply: do not read any SKILL.md.
```

### Answer to Q1

**State packaging = structured system prompt + injected workspace files + skill catalog + memory.**

There IS significant prompt engineering. The state is NOT thrown raw at the agent. Instead:
- System prompt provides structured guidance sections
- Bootstrap files provide user-customizable context
- Skills provide domain expertise on-demand (listed in prompt, read when needed)
- Memory provides persistent recall across sessions
- Runtime info provides environmental awareness

---

## Q2: How Does OpenClaw Guide Agent Self-Evolution?

### Finding: There Is No Magic Self-Improvement Loop

OpenClaw does NOT have explicit "self-improvement code." Evolution is emergent from:

1. **Skills as mandatory pre-check**: The agent is FORCED to scan skills before every reply. This means if a skill exists for a task, the agent will find and follow it. Adding a new skill immediately changes agent behavior.

2. **Memory system**: `MEMORY.md` + `memory/*.md` enable persistent recall. The system prompt mandates: "Before answering anything about prior work, decisions, dates, people, preferences, or todos: run memory_search."

3. **Workspace files as persistent rules**: `AGENTS.md` is user-editable and persists across sessions. Rules added there become permanent agent behavior.

4. **Heartbeat system**: `src/infra/heartbeat-runner.ts` periodically wakes the agent to review status. This enables proactive self-check — the agent can notice things that need attention without user prompting.

5. **Sub-agent delegation**: OpenClaw can spawn sub-agents (Codex, Claude Code, Pi) for complex tasks, effectively distributing work to specialized workers.

### How the Agent "Learns"

The learning cycle:
```
User interacts → Agent follows skills → Agent records to MEMORY.md
→ Next interaction → Agent searches memory → Agent adjusts behavior
→ User edits AGENTS.md/SOUL.md → Persistent behavior change
```

There is no automatic "lesson capture" mechanism in OpenClaw itself. The agent writes to memory files through its standard file editing tools. The human can also directly edit workspace files to shape behavior.

### Key Difference from Our Approach

OpenClaw relies on:
- **Structured system prompt** (not raw context dumping)
- **Mandatory skill scanning** (forced, not optional)
- **Memory as first-class tool** (not just file storage)
- **Workspace files as persistent configuration** (user-editable, session-persisted)

Our project's advantage:
- We have more specialized tools (CDMCP, GOOGLE.*, WHATSAPP, etc.)
- We have a richer skill system with `for_agent.md` per-tool docs
- We have experience/lesson capture (`SKILLS learn`)
- OPENCLAW provides a sandboxed execution environment

---

## Implications for Our OPENCLAW Tool

### 1. Protocol Update (Done)
- System prompt now follows OpenClaw's section structure
- Skills are mandatory pre-scan
- `--openclaw-experience` enables agent lesson capture
- `--openclaw-status` enables agent status awareness

### 2. Key Patterns to Adopt

| Pattern | OpenClaw | Our Implementation |
|---------|----------|-------------------|
| Skills in system prompt | Mandatory scan | ✅ Implemented in `protocol.py` |
| Memory recall | `memory_search` tool | Partially (learnings file) |
| Bootstrap files | AGENTS.md, SOUL.md, etc. | Use `for_agent.md` + skills |
| Heartbeat | Periodic self-check | TODO: Implement in pipeline |
| Sandbox | Docker-based | ✅ Process-level in `sandbox.py` |
| Sub-agents | Codex/Claude Code | Future: Support multiple backends |

### 3. What We Should NOT Copy

- OpenClaw's complexity around channel routing (Telegram, Discord, etc.) — we use CDMCP
- The MCP tool wrapping — we have our own tool system
- The npm/TypeScript build system — we use Python
