# OpenClaw Gap Analysis v4: Post-Source-Code Research

Date: 2026-03-06  
Context: After cloning and analyzing OpenClaw source code (`tmp/openclaw/`), comparing architectural patterns with our project's implementation. See `2026-03-06-openclaw-source-analysis.md` for detailed source findings.

---

## What Changed Since v3

v3 identified "operational infrastructure" as the remaining gap — mechanisms that ensure a weaker agent finds and uses the right knowledge at the right time. Since then:

| v3 Action Item | Status |
|----------------|--------|
| OPENCLAW tool created (prototype) | ✅ Built with CDMCP, sandbox, protocol, pipeline, GUI |
| Skill chaining guidance | ✅ In `task-orchestration` and `recipes` skills |
| Dependency discovery mandate | ✅ Added to `logic/AGENT.md` and `tool-development-workflow` |
| Code-level guardrails (sandbox) | ✅ `OPENCLAW/logic/sandbox.py` with protected patterns |
| Blueprint reuse awareness | ✅ Updated `avoid-duplicate-implementations` skill |

**Source code analysis reveals NEW gaps not visible from documentation alone.**

---

## Q1: Does OpenClaw Auto-Formulate Skills From Experience?

**No.** This is a common misconception. OpenClaw does NOT automatically create skills from errors or experience.

What OpenClaw actually does:
- Agent writes to `MEMORY.md` using standard file tools (read/write/edit)
- `memory_search` enables semantic recall across memory files
- Skills are created manually through the `skill-creator` skill
- Skills are shared via ClawHub marketplace
- The human edits `AGENTS.md`/`SOUL.md` to shape persistent behavior

**Our project is actually AHEAD here**: Our `openclaw` skill defines an explicit Error→Lesson→Rule→Skill→Hook pipeline with `SKILLS learn`, `SKILLS analyze`, and `SKILLS suggest`. OpenClaw has no equivalent.

However: **neither project has truly automatic skill formulation.** The pipeline exists but still requires agent or human initiative to execute each step.

## Q2: When Should Agents Formulate Skills vs Tools?

| Dimension | Formulate a SKILL | Formulate a TOOL |
|-----------|-------------------|------------------|
| **Nature** | Heuristic, context-dependent | Mechanical, deterministic |
| **Reuse** | Advisory — agent reads and interprets | Executable — system runs automatically |
| **Examples** | "How to debug CDMCP sessions", "When to use retry patterns" | "Download iCloud photos", "Send bulk WhatsApp messages" |
| **Trigger** | Pattern of repeated judgment calls | Pattern of repeated mechanical steps |
| **Maintenance** | Updated by editing markdown | Updated by editing code |
| **Error profile** | Agent may misinterpret guidance | Code may have bugs but is deterministic |
| **Signal** | 3+ lessons on same theme → consolidate into skill | 3+ times writing same script → wrap into tool |

**Decision heuristic for the agent:**

```
IF the task requires judgment, context, or varies case-by-case
  → Formulate a SKILL (write SKILL.md with guidance)

IF the task is the same sequence every time and can be scripted
  → Formulate a TOOL (create tool with main.py + setup.py)

IF the task is 50/50 (some judgment + some automation)
  → Formulate a SKILL with bundled scripts/ (OpenClaw pattern)
```

**Currently missing in our system:** No skill or guideline tells the agent WHEN to create a skill vs a tool. This is a gap.

---

## New Gaps Discovered (Post-Source Analysis)

### Gap 1: Mandatory Skill Scanning in System Prompt

**OpenClaw**: System prompt contains `## Skills (mandatory)` — agent MUST scan skill descriptions before EVERY reply. If a skill matches, the agent reads its SKILL.md before proceeding.

**Our project**: Skills are listed in Cursor's agent skills section with descriptions. Cursor provides softer guidance ("check if any available skills can help"). An agent CAN skip skill scanning.

**Impact**: A weaker agent on our project may not discover relevant skills for a task. OpenClaw's enforcement is structural (hardcoded in system prompt), ours is advisory.

**Fix**: Create a bootstrap skill or rule that forces skill scanning, or integrate mandatory scanning into the OPENCLAW protocol (already done for remote agents).

### Gap 2: Memory as First-Class Semantic Search

**OpenClaw**: `memory_search` tool performs semantic search over `MEMORY.md` + `memory/*.md`. Agent is mandated to search before answering about prior work.

**Our project**: `runtime/experience/lessons.jsonl` is file-based. Agent must grep or read the file manually. No semantic search capability. No mandate to check memory before acting.

**Impact**: Agent doesn't recall past lessons unless explicitly directed. Experience capture exists but recall is friction-heavy.

**Fix**: Build `--openclaw-memory-search` command with keyword/semantic search. Add "check lessons before starting" to the system prompt.

### Gap 3: Centralized Bootstrap Context

**OpenClaw**: Embeds `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `IDENTITY.md`, `USER.md`, `BOOTSTRAP.md` directly into system prompt as "Project Context."

**Our project**: `AGENT.md` files scattered across `logic/`, `tool/*/`, `tool/*/logic/`. No single bootstrap bundle. Agent must discover and navigate these documents.

**Impact**: New agent doesn't get essential context in its first interaction. Must find and read multiple `AGENT.md` files to understand the project.

**Fix**: Create a centralized `BOOTSTRAP.md` or `AGENTS.md` at project root that aggregates essential context from all `AGENT.md` files. Or: OPENCLAW protocol already does this via `build_system_prompt()` for remote agents.

### Gap 4: Progressive Disclosure in Skills

**OpenClaw**: `skill-creator` skill explicitly teaches 3-level progressive disclosure:
1. Metadata (name + description) ~100 words — always in context
2. SKILL.md body — loaded when triggered (<5k words)
3. Bundled resources (scripts/, references/, assets/) — loaded on demand

**Our project**: Skills vary in structure. Some are lean, some are monolithic. No enforced progressive disclosure pattern. No bundled `scripts/` or `references/` pattern.

**Impact**: Large skills waste context tokens. Agents can't selectively load parts of a skill.

**Fix**: Update `skill-creation-guide` skill with progressive disclosure requirements. Add `scripts/` and `references/` support.

### Gap 5: Skill-vs-Tool Formulation Guidance

**OpenClaw**: Has `skill-creator` skill with detailed creation workflow. But no explicit guidance on when to create a skill vs when to create a CLI tool.

**Our project**: Has `tool-development-workflow` and `skill-creation-guide` but no guidance on choosing between them.

**Impact**: Agent defaults to whatever it encounters first. May create a skill when a tool would be more appropriate (or vice versa).

**Fix**: Create a decision-tree skill or add a section to `openclaw` skill.

### Gap 6: Heartbeat / Periodic Self-Check

**OpenClaw**: Heartbeat system periodically wakes the agent to review status. Agent can proactively notice issues, send reminders, check on background tasks.

**Our project**: No equivalent. Agent only responds when prompted. OPENCLAW pipeline has a task loop but no self-initiated review cycle.

**Impact**: Agent cannot proactively detect and report issues between user interactions.

**Fix**: Add heartbeat to OPENCLAW pipeline that periodically checks task status and project health.

### Gap 7: Agent Bootstrap Protocol (Still Incomplete)

**OpenClaw**: Every interaction loads the full system prompt with all bootstrap files. New sessions automatically get skills, memory, workspace context.

**Our project**: Agent bootstrap relies on Cursor's agent skills feature + `.cursor/rules/`. But a new agent doesn't know to read `logic/AGENT.md` or check dependencies before coding.

**Impact**: Despite v3's "mandatory dependency discovery" additions, enforcement is still documentation-based, not structural.

**Fix**: Move critical bootstrap context into Cursor rules (`.cursor/rules/`) which are auto-loaded. Or: Make the OPENCLAW protocol the primary interaction mode for agent tasks.

---

## The Simulation: New Agent + Real Task

### Scenario (same as v3 but updated with source research)

A Sonnet-class agent takes over the project. User asks: "Send Happy New Year messages to all WhatsApp contacts."

### What Happens Now (Post v4)

1. **Agent scans Cursor agent skills** → finds `task-orchestration`, `recipes`, `preflight-checks`
2. **Reads `task-orchestration`** → learns to decompose task into steps
3. **Discovers WHATSAPP tool** via `AGENT.md` in `tool/WHATSAPP/`
4. **Reads WHATSAPP `AGENT.md`** → learns about CDMCP, rate limits, session management
5. **Checks `preflight-checks`** → runs pre-flight validation
6. **Starts execution** → but...

### Where It Still Breaks

| Step | Failure Point | OpenClaw Equivalent |
|------|--------------|---------------------|
| Memory recall | Agent doesn't check `lessons.jsonl` for past WhatsApp gotchas | `memory_search` is mandated in system prompt |
| Skill scanning | Agent might skip skills or read wrong one | `## Skills (mandatory)` forces scanning |
| Error recovery | Agent doesn't know to record lesson when hitting rate limit | No auto-capture in OpenClaw either, but memory is more accessible |
| Tool creation | If WHATSAPP tool is incomplete, agent doesn't know whether to fix tool or create skill | No guidance on skill-vs-tool decision |
| Self-check | After sending messages, no heartbeat to verify delivery | OpenClaw heartbeat verifies completion |

### Honest Assessment

**Can a Sonnet agent complete this task?** Probably yes, with 2-3 attempts. The skills and documentation are good enough. But:
- It will be slower than necessary (no memory recall)
- It won't capture what it learned (no mandatory lesson recording)
- It won't know to create a reusable automation vs document the workflow
- It won't proactively verify the result

**Can it reach Opus-level development capability?** With our skills, it can reach ~70-80% effectiveness for KNOWN patterns. The remaining 20-30% is:
- Novel situations where no skill exists
- Judgment calls about architecture
- The initiative to CREATE new skills/tools from experience
- Self-verification through heartbeat/monitoring

---

## Action Items (Priority Order)

### P0: Critical (Blocks autonomous operation)

1. **Memory search command** — `--openclaw-memory-search <query>` in sandbox, keyword search over `lessons.jsonl`
2. **Mandatory lesson check** — Add to OPENCLAW system prompt: "Before starting any task, search lessons for relevant prior experience"
3. **Skill-vs-tool decision guide** — Add to `openclaw` skill or create new decision-tree skill

### P1: High (Significantly improves autonomy)

4. **Centralized BOOTSTRAP.md** — Aggregate essential `AGENT.md` context into single file
5. **Progressive disclosure enforcement** — Update `skill-creation-guide` with 3-level pattern
6. **Heartbeat in OPENCLAW pipeline** — Periodic status check between iterations

### P2: Medium (Polish and robustness)

7. **Auto-suggest skill vs tool** — When `SKILLS suggest` runs, classify suggestion type
8. **Skill bundled resources** — Support `scripts/` and `references/` in skill directories
9. **Bootstrap enforcement in Cursor rules** — Ensure critical skills are auto-loaded

---

## Summary

| Category | OpenClaw | Our Project | Gap Direction |
|----------|----------|-------------|---------------|
| Skills system | Mandatory scan, progressive disclosure, marketplace | Rich skills, scattered loading | OpenClaw > Us |
| Memory/experience | Semantic search, mandated recall | Lesson capture, manual recall | OpenClaw > Us |
| Error→Skill pipeline | Manual (skill-creator) | Semi-automated (SKILLS analyze/suggest) | Us > OpenClaw |
| Tool ecosystem | Basic (read/write/exec/grep) | Rich (CDMCP, WHATSAPP, etc.) | Us > OpenClaw |
| Bootstrap context | Centralized, auto-loaded | Distributed, manually discovered | OpenClaw > Us |
| Self-check | Heartbeat system | None | OpenClaw > Us |
| Agent guidance | Workspace files (AGENTS.md, SOUL.md) | AGENT.md + skills | Comparable |
| Sandbox | Docker-based | Process-level | OpenClaw > Us (but ours is simpler) |
