# runtime/brain/

Persistent task and context memory for AI agents. Read at session start, updated during work, saved before session end.

## Files

| File | Purpose | Updated by |
|------|---------|------------|
| `tasks.json` | Active task list with status tracking | `BRAIN add/done/delete` |
| `tasks.md` | Human-readable task list (auto-rendered) | `BRAIN add/done/delete` |
| `context.md` | Current working context and resumption state | `BRAIN snapshot` |
| `activity.jsonl` | Activity journal with optional artifact tracking | `BRAIN log` |
| `blueprint.json` | Brain architecture configuration (tiers, backends, guidance) | Developer |

## Architecture

The brain uses a pluggable three-tier architecture defined in `blueprint.json`:

| Tier | Purpose | Path |
|------|---------|------|
| **working** | Hot state (tasks, context, activity) | `runtime/brain/` |
| **knowledge** | Lessons, skills, institutional memory | `runtime/experience/` |
| **episodic** | Agent personality, long-term memory | `runtime/experience/{brain_type}/` |

Each tier can use a different storage backend (currently `flatfile`). See `logic/brain/for_agent.md` for the backend interface and upgrade path.

## How It Works

1. **Session start**: IDE hook reads brain files and injects content into the agent's context.
2. **During work**: Hook periodically reminds the agent to check and update brain files.
3. **Session end**: Hook enforces USERINPUT and reminds the agent to save brain state.

## Guidance Auto-Adaptation

The `blueprint.json` `guidance` section maps documentation keys to files:
- `bootstrap` → `for_agent.md` (agent bootstrap protocol)
- `reflection` → `for_agent_reflection.md` (self-improvement protocol)

When a new brain type is created, it can reference different guidance docs, enabling documentation to auto-adapt to the brain architecture.

## Adding a New Brain Type

1. Copy and modify `blueprint.json` with different tier configurations
2. Implement a new backend in `logic/brain/backends/` if needed
3. Update guidance references to point to brain-type-specific docs
4. Register the backend in `logic/brain/blueprint.py::BACKEND_REGISTRY`

See `interface/brain.py` for the programmatic API.
