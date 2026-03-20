# Brain Blueprints

A brain blueprint is a versioned package defining how an AI agent stores, retrieves, and manages knowledge. Each blueprint contains a `blueprint.json` (architecture spec) and auxiliary files (default SOUL, guidance overrides, backend configuration).

## Naming Convention

```
<type>-<YYYYMMDD>
```

The date suffix enables iterative updates while preserving older versions.

## Available Blueprints

| Blueprint | Backend | Description |
|-----------|---------|-------------|
| `clitools-20260316` | flatfile | Project default. File-based three-tier memory with BRAIN CLI. Zero dependencies. |
| `claude-mem-20260316` | flatfile + L0/L1/L2 | Context compression focus. Heuristic L0 summaries, progressive disclosure. |
| `rag-20260316` | flatfile + vector (planned) | Semantic retrieval via sentence-transformers + FAISS. |
| `openclaw-20260316` | flatfile (+ hybrid optional) | OpenClaw-inspired: Markdown-canonical, hybrid search, pre-compaction flush, self-improvement loop. |

## Creating an Instance from a Blueprint

```bash
BRAIN session create my-brain --type openclaw-20260316
```

This copies the blueprint's `blueprint.json` and default files into a new instance directory.

## Creating a New Blueprint

1. Create a directory: `logic/brain/blueprint/<name>-<YYYYMMDD>/`
2. Add `blueprint.json` — defines tiers, backends, features
3. Add `defaults/` — default SOUL.md, MEMORY.md (optional)
4. Add `README.md` — describes the blueprint's philosophy and usage
5. If a new backend is needed, implement in `logic/brain/backends/`
6. Validate: `python3 -c "from interface.brain import audit_blueprint; print(audit_blueprint('<name>'))"` 

Full specification: `logic/tutorial/brain/README.md`

## Base (Shared Ecosystem Rules)

All blueprints inherit from `base.json`, which defines ecosystem rules shared across every brain:
- **Guidance**: bootstrap docs (`for_agent.md`, `for_agent_reflection.md`)
- **Hooks**: IDE integration hooks (session start, post-tool-use, stop)
- **Directory conventions**: tracked vs. gitignored symmetric directories
- **Documentation pattern**: `README.md` / `for_agent.md` / `for_agent_reflection.md`
- **Quality commands**: `TOOL --audit code`, `TOOL --lang audit`
- **Search commands**: `TOOL --search all`, `BRAIN recall`

Blueprints only need to define **what's different** — tiers, backends, and type-specific features. The `"inherits": "base"` field indicates this inheritance. At load time, `load_blueprint()` merges `base.json` underneath, so blueprint-specific values always take precedence.

## What Makes Blueprints Different

Each blueprint differs in:
- **Backend**: How data is stored (flatfile, SQLite FTS5, vector DB, external process)
- **Tier structure**: How tiers are organized within an instance
- **Defaults**: Starting personality (SOUL.md), pre-loaded knowledge
- **Features**: Type-specific capabilities (L0 compression, hybrid search, decay)
- **Context injection**: How and when brain data enters agent context
- **Self-improvement**: Feedback loop configuration (confidence thresholds, pattern detection)
- **Triggers**: Event-driven actions (pre-compaction flush, digest reminders)
- **Dependencies**: External packages needed
