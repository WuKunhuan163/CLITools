# AITerminalTools

A symmetrical tool management ecosystem for AI agents and developers. Every tool is a terminal command. Every command follows the same pattern. Agents inherit institutional memory across sessions.

**Mission**: Enable any context-free AI IDE assistant to achieve OpenClaw-level agent capability from a cold start — completing developer tasks, embracing the ecosystem, and accumulating visible intelligence growth through pluggable brain architectures and session-based memory.

**Vision**: Assistants that don't just execute tasks, but learn from them — creating skills, building tools, and growing institutional memory that persists across sessions. Intelligence becomes visible, transferable, and continuously improving.

### What is a Metacognitive Development Assistant?

An assistant with metacognitive development capability exhibits two alternating traits:

1. **Self-Iteration** — Improves its own capability while working. Each task is faster and more efficient than the last. Lessons from mistakes become skills; skills become infrastructure; infrastructure becomes automatic.

2. **Proactive Environment Improvement** — Identifies and fixes problems in the system itself, even when not directly related to the current task. Spots a documentation gap while coding? Fixes it. Finds a missing test pattern? Creates it.

3. **User-Centric Delivery** — Always consider what the user actually sees and experiences. After fixing a bug, verify that the fix is delivered to the user's environment (restart servers, refresh caches, take browser screenshots). Think of the user as a boss watching over your shoulder — can they see progress? Can they confirm results? Anticipate friction points (stale caches, unrestarted services, unflushed state) and resolve them before reporting completion.

These traits co-evolve like human civilization's relationship with tools: create better tools, use them to improve the environment, the improved environment enables new tools. Early humans mastered fire; we no longer study fire — we study AI. Similarly, once an assistant builds reliable infrastructure for a pattern, it stops re-deriving that pattern and moves on to harder problems. The knowledge pipeline (`Lesson → Skill → Infrastructure → Hook`) is the formalization of this cycle.

## For AI Agents

**If you are an AI assistant working in this codebase, read [`AGENT.md`](AGENT.md) first.** It contains the bootstrap protocol, key commands, session phases, and everything you need to operate effectively. Start at Section 0.

Quick reference:
- `TOOL --eco guide` — onboarding walkthrough
- `TOOL --eco nav` — browse the skills dictionary tree
- `TOOL --eco search "query"` — find tools, skills, lessons, docs
- `SKILLS show <name>` — read a specific development skill

## Quick Start

```bash
# 1. Clone + setup (auto-detects IDE, deploys hooks)
python3 setup.py

# 2. Install a tool
TOOL install USERINPUT

# 3. Run it — every installed tool is a standalone terminal command
USERINPUT --hint "Hello! AITerminalTools is operational."
```

After `setup.py`, all installed tools live in `bin/` and are callable directly from any terminal.

## Core Design Principles

### CLI-First

Every tool is a terminal command. Every command follows `TOOL_NAME [--flags] [command] [args]`. This makes tools composable, testable, scriptable, and discoverable by both humans and AI agents.

### Symmetrical Architecture

The project enforces a uniform directory pattern at every level:

```
root/                        tool/<NAME>/
├── logic/      (internal)   ├── logic/      (internal)
├── interface/  (public API) ├── interface/  (public API)
├── hooks/      (lifecycle)  ├── hooks/      (lifecycle)
├── AGENT.md             ├── AGENT.md
├── AGENT_REFLECTION.md  ├── AGENT_REFLECTION.md
└── README.md                └── README.md
```

**Import rule**: Tools import from `interface.*`, never from `logic.*` directly. This enables quality auditing, safe refactoring, and cross-tool communication.

### Double-Dash Convention

All root-level symmetric commands use `--` prefixes to avoid collision with tool names:

```bash
TOOL --search all "query"    # Search everything
TOOL --dev create MY_TOOL    # Scaffold new tool
TOOL --audit code            # Code quality audit
TOOL --audit imports         # Import rule enforcement
TOOL --lang audit zh         # Translation coverage
```

Tool-specific commands omit the prefix: `BRAIN reflect`, `SKILLS list`, `USERINPUT --hint`.

### Progressive Context Disclosure

Agents don't read everything at once. The system uses layered docs:
- **L0** (`README.md`): Stable overview. What this is.
- **L1** (`AGENT.md`): Operational guide. How to work with it.
- **L2** (`AGENT_REFLECTION.md`): Self-improvement. What gaps exist.

This pattern repeats at root, logic/, and tool/ levels.

### Multi-Tier Knowledge Pipeline

```
Work → Lesson → Skill → Infrastructure → Hook
```

Each step automates the previous one. Agents are expected to advance along this pipeline, not stay at "lesson."

### Skills as a Dictionary Tree

Skills are organized as a hierarchical tree — like a dictionary you navigate by topic. Each directory level narrows the subject. Category directories contain `README.md` (what's here) and `AGENT.md` (navigation: what's below, what's above). Leaf directories contain `SKILL.md`.

```
skills/
├── _/                # Foundational principles (modularization, symmetric design, meta-agent)
├── development/      # Building tools and commands
├── quality/          # Code health and auditing
├── infrastructure/   # Runtime patterns (caching, display, error handling)
├── workflow/         # Agent operations and self-improvement
├── browser/          # Browser automation
├── IDE/              # IDE-specific (Cursor)
└── clawhub/          # External marketplace skills
```

The hierarchy itself carries information. An agent searching for "how to write tests" navigates `skills/` → `development/` → `unit-test-conventions/`. The path encodes the topic without reading any file.

### Layered Documentation with AGENT.md

Every directory in the project has up to three documentation files:

| File | Audience | Purpose |
|---|---|---|
| `README.md` | Humans | What this is, how to use it |
| `AGENT.md` | AI agents | Navigation guide: what's here, what's below, what's above |
| `AGENT_REFLECTION.md` | Self-improvement | Known gaps, improvement opportunities |

This is the project's modularization principle applied to documentation: each level of the directory tree is a logical layer, and each layer tells its readers what they can find by going deeper. `AGENT.md` at every level creates a "filesystem for knowledge" — agents navigate it like `cd` and `ls`, always knowing where they are and where to go next.

The rationale: modularized code without modularized documentation is half-modularized. If every `logic/` subdirectory has clean interfaces but no `AGENT.md`, a context-free agent must read source code to understand what's there. Adding `AGENT.md` makes the structure self-describing. Run `TOOL --audit skills` to verify documentation coverage.

## Architecture

```
AITerminalTools/
├── logic/           # Shared core (internal implementation)
│   ├── brain/       # Pluggable memory architecture
│   ├── assistant/   # LLM-powered assistant subsystem
│   ├── audit/       # Code quality and import analysis
│   ├── dev/         # Developer workflow automation
│   └── ...
├── interface/       # Stable facade (tools import from here)
├── tool/            # All tools (each has logic/, interface/, hooks/)
├── bin/             # Executable symlinks for installed tools
├── skills/          # Dictionary-tree of agent skills (hierarchical)
├── runtime/         # Git-tracked institutional memory
│   └── experience/  # Lessons, suggestions, evolution history
├── AGENT.md     # Agent bootstrap guide
└── AGENT_REFLECTION.md  # Self-improvement protocol
```

**Transient directories** (gitignored): `data/`, `logs/`, `tmp/`
**Tracked data**: `runtime/`, `skills/`, `research/`

## Brain Ecosystem

Pluggable brain blueprints — different memory architectures for AI agents. A blueprint defines how an agent stores, retrieves, and manages knowledge across sessions.

```
logic/brain/
├── blueprint/        # Versioned architecture definitions
│   ├── base.json     # Shared ecosystem rules (all blueprints inherit)
│   └── <name>/       # Individual blueprints (blueprint.json + README.md)
├── instance/         # Session management
├── utils/            # Audit and validation
├── backends/         # Storage engine implementations
└── loader.py         # Blueprint loading and merging
```

Blueprints are versioned (`<type>-<YYYYMMDD>`) and inherit shared ecosystem rules from `base.json`. Brain instances are isolated namespaces with their own working memory, knowledge, and episodic data.

```bash
BRAIN session types                              # List available blueprints
BRAIN session create my-brain --type <blueprint>  # Create instance
BRAIN session list                                # List instances
BRAIN session export my-brain                     # Export to zip
```

See `logic/tutorial/brain/README.md` for the full blueprint development guide.

## Using with AI IDEs

If you use this project with an AI IDE (Cursor, Copilot, Windsurf), **just type your task**. The system automatically provides context, guides self-checking, and maintains a feedback loop.

| Layer | What it does | You need to do |
|-------|-------------|---------------|
| `setup.py` | Auto-detects IDE, deploys hooks and rules | Run once |
| Session hooks | Inject brain context and USERINPUT directive | Nothing |
| IDE rules | Guide quality, testing, feedback patterns | Nothing |
| USERINPUT | Feedback loop — assistant asks, you respond | Respond naturally |
| BRAIN | Cross-session memory — tasks, activity, progress | Nothing |

**If the assistant seems lost**, paste:
> Read AGENT.md Section 0 and follow the bootstrap protocol. Then BRAIN reflect and USERINPUT --hint.

## Discovering Tools and Skills

```bash
TOOL status                       # All registered tools with install status
TOOL --search tools "query"       # Find tools by description
TOOL --search skills "query"      # Find skills by topic
TOOL --search all "query"         # Search everything
SKILLS list                       # All available skills
BRAIN recall "topic"              # Search institutional memory
```

Tool details, specific commands, and skill catalogs are intentionally kept in `AGENT.md` and per-tool docs — not here — because they change frequently.

## Developer Workflow

```bash
TOOL --dev create MY_TOOL         # Scaffold from template
TOOL --dev sync                   # Align git branches
TOOL --dev audit-test MY_TOOL     # Audit test conventions
TOOL --audit imports              # Import quality analysis
TOOL --audit quality              # Hooks, interface, skills validation
```

See `SKILLS show tool-development-workflow` for the full guide.

## For AI Agents

Read `AGENT.md` in this directory. That file is your primary reference. Key entry points:

- `AGENT.md` — Architecture guide, bootstrap protocol, conventions
- `AGENT_REFLECTION.md` — Self-improvement protocol and system gaps
- `TOOL --search all "<query>"` — Find anything
- `BRAIN reflect` — Self-check protocol + active reminders
- `USERINPUT --hint "summary"` — Report to user (blocking feedback loop)

## Roadmap

- **Assistant System**: Design, develop, and test the built-in assistant framework that enables LLM-powered agents to use these tools autonomously. This includes multi-model routing, session management, and the meta-agent workflow that leverages the full ecosystem.

## Contribution

Active development happens on the `dev` branch. Run `SKILLS show tool-development-workflow` for the full development guide.
