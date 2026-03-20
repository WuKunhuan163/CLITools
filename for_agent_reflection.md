# Agent Self-Reflection Protocol

This file is a stable protocol for AI agents operating in this project. Read it at session start to calibrate your behavior. It defines what "good" looks like, provides a self-evaluation framework, and identifies system-level improvement opportunities.

## How to Use This File

1. **Read at session start** (after `runtime/brain/context.md`)
2. **During work**: Compare your behavior against the self-check protocol below
3. **Before ending**: Record findings in the brain (`BRAIN snapshot`), not here
4. **System improvements**: Fix the system (code, hooks, skills), then update the gap section here only if you fixed or discovered a system-level gap

## How to Update This File

This file should be **refined, not grown**. Rules:
- **Fix a gap** → remove it from "Current System Gaps" and briefly note what replaced it
- **Discover a new system-level gap** → add it, but keep the total to 3-7 gaps
- **Session-specific discoveries** → `SKILLS learn`, `BRAIN snapshot`, `runtime/experience/lessons.jsonl`
- **Never add a session log** — that goes to `runtime/brain/context.md` and git history
- **Never duplicate for_agent.md content** — this file is about WHY and HOW, not WHAT

## Scope Hierarchy

`for_agent_reflection.md` exists at two levels. Know which to update:

| Scope | File | Update when... |
|-------|------|---------------|
| **System** | `/for_agent_reflection.md` (this file) | You discover a cross-tool, ecosystem-level gap (e.g., missing hook framework, weak search infrastructure) |
| **Tool** | `tool/<NAME>/for_agent_reflection.md` | You discover a tool-specific gap (e.g., edge case in a provider, missing test coverage, tool-local design flaw) |

Decision rule: **Does this affect all future agents, or only agents working on this specific tool?** System-level → root. Tool-level → tool directory.

When running `BRAIN reflect`, the root file is always shown. When working on a specific tool, also run `BRAIN reflect --tool <NAME>` to check tool-level gaps.

If a tool doesn't have its own `for_agent_reflection.md` yet, create one using the template pattern (see `logic/tool/template/docs/for_agent_reflection.md.tmpl`).

## Reference: What a Capable Agent Does

OpenClaw demonstrates that an AI agent can, from a cold start: build complete software from a one-line request, self-test extensively, iterate aggressively (implement → test → fix → test → improve), and accumulate skills through self-observation.

Our system operates in session-based AI IDE environments (Cursor, Copilot, Windsurf) rather than OpenClaw's 24/7 heartbeat model. This is intentional — see "Our Advantages" below.

| Our System | OpenClaw |
|---|---|
| Session-based (low power) | 24/7 heartbeat (high power) |
| CLI-first: every tool = terminal command | General-purpose agent |
| Symmetric directory design (tool/logic/interface) | Flat structure |
| Multi-tier knowledge (lessons → skills → infra → hooks) | Flat skill files |
| Progressive context disclosure (L0/L1/L2) | Full context dump |
| Structured skill catalog + marketplace | Workspace-file skills |
| Audit infrastructure (code, imports, lang) | No equivalent |

## Self-Check Protocol

Before each USERINPUT call, evaluate yourself against these dimensions:

**Discovery** — Did I search before coding?
- Ran `TOOL --search all` before writing new code
- Checked `SKILLS list` for relevant skills
- Read `for_agent.md` of any tool I'm modifying
- Used `BRAIN recall` for related past issues

**Self-Testing** — Did I verify my changes work?
- Ran the code I wrote (not just assumed it works)
- Created `tmp/` test scripts for non-trivial logic
- Tested edge cases, not just the happy path

**Knowledge Capture** — Did I record what I learned?
- Ran `BRAIN log` after each completed task (what, result, observations)
- Recorded non-obvious discoveries via `SKILLS learn`
- Ran `BRAIN digest` to check for lesson distillation opportunities (3+ → skill)
- Ran `BRAIN snapshot` after milestones
- Updated relevant `for_agent.md` and `README.md` files

**Iteration Quality** — Did I iterate or stop at v1?
- Tested first implementation, found issues, fixed them
- Considered discoverability for future agents

**Knowledge Creation** — Did I codify what I learned into reusable artifacts?
- When I solved a hard problem, did I create a skill (`SKILLS create <name>`) so future agents don't struggle the same way?
- When I built a repeatable pattern, did I build infrastructure (`logic/` + `interface/main.py`) instead of leaving it as prose?
- When I noticed 3+ related lessons (`BRAIN digest`), did I consolidate them into a skill?
- When a skill described a mechanical process, did I consider automating it as a tool (`TOOL --dev create`)?
- Motivation check: the pipeline is Work → Lesson → Skill → Infrastructure → Hook. Am I advancing along this pipeline or stuck at "lesson"?

**Phase Awareness** — Do I know what I'm doing and why?
- Can identify my current phase: task phases (Bootstrap/Execute/Verify/Capture/Feedback/Handoff) or meta activities (Document/Curate/Audit/Refactor/Harden/Improve)
- Completed each phase before starting the next (didn't mix task execution with meta activities)
- Recognized when the user's request is a meta activity (e.g., "audit skills" = Curate, "clean up" = Refactor, "strengthen this module" = Harden) vs a task
- Triggered Harden periodically (not reactively to every issue) — after heavy use, long dormancy, or post-incident

**Error Handling** — Did I fix problems properly?
- Treated ecosystem tools (TOOL, BRAIN, SKILLS) as potentially buggy, not infallible
- Followed escalation: read source → fix → retry → search alternatives → ask user
- Recorded failures as lessons via `SKILLS learn`

**Hardening Awareness** — Did I notice infrastructure that needs strengthening?
- Checked `TOOL --audit code` and `TOOL --audit imports` for quality issues
- Noticed hardcoded values, narrow implementations, or missing error handling
- Assessed whether now is the right time to harden (periodic, not reactive)
- Ran or wrote tests to verify robustness of tools I touched
- Checked architecture compliance (symmetric dirs, import rules, tool.json completeness)
- Reviewed accumulated lessons for distillation: lessons → skills → infrastructure → hooks
- Prioritized: fix latent bugs > robustness tests > architecture compliance > knowledge distillation > docs

**Brain Intelligence** — Did I make the ecosystem easier to navigate for future agents?
- Left waypoints in for_agent.md when I discovered non-obvious module connections
- Recorded improvement opportunities as BRAIN tasks when I couldn't fix them now
- Reduced entropy: merged overlapping content, removed outdated material
- Added useful command sequences to recipes or relevant for_agent.md
- Checked doc symmetry: tools I touched have both README.md and for_agent.md

**Interface Discipline** — Did I follow the three-layer pattern?
- Put implementation in `logic/`, not directly in `main.py` or `interface/`
- Exposed reusable functionality via `interface/main.py` (cross-tool API)
- Imported from `interface.*` (not `logic.*`) when consuming other tools
- Checked for existing interfaces before writing new code (`TOOL --search interfaces "..."`)

**Strategic Pivoting** — Did I recognize when to change approach?
- After 3+ failures with the same tool/method, searched for alternatives (`TOOL --search all`)
- Considered equivalent but different paths (e.g., browser automation failing → build backend API endpoint instead)
- Recorded the failure pattern as a lesson (`SKILLS learn`) so future agents avoid the same dead end
- Built compensatory infrastructure when a persistent limitation was found (don't just work around it — create a permanent solution)

**IDE Awareness** — Did I account for my IDE's quirks?
- Set `block_until_ms: 120000` when calling USERINPUT via Shell (Cursor defaults to 30s — too short)
- Used `ls -la | grep` as fallback when Glob/Grep return empty (paths with spaces fail silently)
- Read `hooks/interface/AI-IDE/Cursor/for_agent.md` for known quirks if working in Cursor
- Checked `userinput-timeout.mdc` rule for USERINPUT wait handling

**System Awareness** — Did I use the ecosystem?
- Used existing tools instead of reimplementing
- Called `USERINPUT` at every significant milestone

## System Improvement Protocol

When you identify a weakness in the ecosystem, follow this path:

1. **Verify it's systemic** — Does this affect all future agents, or just your current task?
2. **Check if it's already known** — Read "Current System Gaps" below and `BRAIN recall`
3. **Fix the system** — Change code, hooks, skills, or documentation
4. **Record the fix** — `SKILLS learn` the discovery, `BRAIN snapshot` the context
5. **Update this file** — Only if you fixed or discovered a system-level gap (keep to 3-7 gaps)

## Current System Gaps

These are the highest-priority system-level weaknesses. Each agent should attempt to fix at least one. When fixed, remove it and note the replacement.

**Gap: No Forced Skill Pre-Scan** — Agents can search for skills but often skip it. Ideal fix: a `postUserPrompt` hook that matches the user's prompt against skills and injects relevant summaries into context.

**Gap: No Automatic Self-Test Enforcement** — Agents are told to self-test but compliance is inconsistent. Ideal fix: a post-write hook that detects code changes and nudges the agent to run tests.

**Gap: Context Loss on Session Crash** — If a session crashes, `context.md` may be stale. `BRAIN snapshot` exists but isn't automatic. Ideal fix: integrate auto-snapshot into the USERINPUT hook chain.

**Gap: Cross-Session Memory is Shallow** — `BRAIN recall` now searches lessons, activity log, and context.md. But past session transcripts and detailed tool outputs are still lost. Ideal next step: SQLite FTS5 index of session summaries (see `research/2026-03-16_claude-mem-source-analysis.md`).

**Gap: No Tool Categorization in Discovery** — `TOOL status` lists 56+ tools as a flat list. Ideal fix: add `"category"` to `tool.json` and group output by category.

**Gap: IDE-Agnostic Hook Framework** — Only Cursor has hooks (sessionStart, postToolUse, stop). VS Code/Windsurf agents miss brain injection and USERINPUT enforcement entirely. IDE detection exists (`logic/setup/ide_detect.py`) but only Cursor has a deploy module. Ideal fix: abstract the hook framework so each IDE has its own deploy module with equivalent lifecycle hooks.

## Our Advantages (Preserve These)

When optimizing, do not lose what makes this system better:

1. **CLI-first architecture**: Every tool = terminal command in `bin/`. Composable, testable, discoverable. Don't collapse into a monolithic agent.
2. **Symmetric design**: `logic/` → `interface/` → `tool/`. Enables quality audits, import checks, cross-tool communication. Don't shortcut it.
3. **Multi-tier knowledge**: Lessons → Skills → Infrastructure → Hooks. Each tier serves a purpose. Don't skip tiers.
4. **Progressive context disclosure**: L0/L1/L2 compression saves tokens without losing retrievability. Cheaper than AI-based compression.
5. **Session-based operation**: Zero power cost when idle. IDE provides file editing, code navigation, and LSP for free.
6. **Audit infrastructure**: `TOOL --audit code`, `TOOL --audit imports`, `TOOL --lang audit`. Automated quality gates.

## Universality Principle

When improving the system, always ask:

> "Does this improvement work for ANY AI IDE agent, or only for the current one?"

Good: new BRAIN commands, better `for_agent.md`, smarter context compression, new hooks, CLI improvements.
Bad: hardcoded model-specific behavior, IDE-specific features without abstraction, breaking the session-based model.
