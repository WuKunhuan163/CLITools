# AITerminalTools

A symmetrical tool management ecosystem for AI agents and developers. Every tool is a terminal command. Every command follows the same pattern. Agents inherit institutional memory across sessions.

**Mission**: Enable any context-free AI IDE assistant to achieve OpenClaw-level agent capability from a cold start — completing developer tasks, embracing the ecosystem, and accumulating visible intelligence growth through pluggable brain architectures and session-based memory.

**Vision**: Assistants that don't just execute tasks, but learn from them — creating skills, building tools, and growing institutional memory that persists across sessions. Intelligence becomes visible, transferable, and continuously improving.

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
├── for_agent.md             ├── for_agent.md
├── for_agent_reflection.md  ├── for_agent_reflection.md
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
- **L1** (`for_agent.md`): Operational guide. How to work with it.
- **L2** (`for_agent_reflection.md`): Self-improvement. What gaps exist.

This pattern repeats at root, logic/, and tool/ levels.

### Multi-Tier Knowledge Pipeline

```
Work → Lesson → Skill → Infrastructure → Hook
```

Each step automates the previous one. Agents are expected to advance along this pipeline, not stay at "lesson."

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
├── skills/          # AI agent skill documents
├── runtime/         # Git-tracked institutional memory
│   └── experience/  # Lessons, suggestions, evolution history
├── for_agent.md     # Agent bootstrap guide
└── for_agent_reflection.md  # Self-improvement protocol
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
> Read for_agent.md Section 0 and follow the bootstrap protocol. Then BRAIN reflect and USERINPUT --hint.

## Discovering Tools and Skills

```bash
TOOL status                       # All registered tools with install status
TOOL --search tools "query"       # Find tools by description
TOOL --search skills "query"      # Find skills by topic
TOOL --search all "query"         # Search everything
SKILLS list                       # All available skills
BRAIN recall "topic"              # Search institutional memory
```

Tool details, specific commands, and skill catalogs are intentionally kept in `for_agent.md` and per-tool docs — not here — because they change frequently.

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

Read `for_agent.md` in this directory. That file is your primary reference. Key entry points:

- `for_agent.md` — Architecture guide, bootstrap protocol, conventions
- `for_agent_reflection.md` — Self-improvement protocol and system gaps
- `TOOL --search all "<query>"` — Find anything
- `BRAIN reflect` — Self-check protocol + active reminders
- `USERINPUT --hint "summary"` — Report to user (blocking feedback loop)

## Contribution

Active development happens on the `dev` branch. Run `SKILLS show tool-development-workflow` for the full development guide.
