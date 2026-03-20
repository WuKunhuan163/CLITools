# logic/brain/ — Agent Memory Architecture

## Overview

Pluggable three-tier memory system for AI agents. Inspired by PlugMem (Microsoft Research, 2026), claude-mem's L0/L1/L2 retrieval, and OpenClaw's Markdown-canonical architecture.

## Directory Structure

```
logic/brain/
├── blueprint/                 # Blueprint definitions (versioned packages)
│   ├── base.json              # Shared ecosystem rules (all blueprints inherit)
│   ├── clitools-20260316/     # Default: file-based, zero dependencies
│   ├── claude-mem-20260316/   # L0/L1/L2 context compression
│   ├── rag-20260316/          # Vector embeddings (planned)
│   └── openclaw-20260316/     # OpenClaw-inspired: hybrid search, self-improvement
├── instance/                  # Instance management (sessions)
│   └── session.py             # BrainSessionManager
├── utils/                     # Audit and validation
│   └── audit.py               # Blueprint auditor (path safety, field validation)
├── backends/                  # Storage engine implementations
│   └── flatfile.py            # Reference implementation
├── base.py                    # Abstract BrainBackend interface
└── loader.py                  # Blueprint loading, merging, backend instantiation
```

## Tiers

| Tier | Purpose | Lifecycle | Default Backend |
|------|---------|-----------|----------------|
| **working** | Hot state: tasks, context, activity | Session-scoped | flatfile |
| **knowledge** | Lessons, skills, institutional memory | Permanent | flatfile |
| **episodic** | Agent personality, long-term memory | Permanent | flatfile |

## Base (Shared Ecosystem Rules)

All blueprints inherit from `logic/brain/blueprint/base.json`, which defines:
- **Guidance**: bootstrap docs, reflection protocol, onboarding skill
- **Hooks**: IDE integration (session start, post-tool-use, stop)
- **Context injection**: what brain data gets injected into agent context
- **Directory conventions**: tracked vs. gitignored symmetric directories
- **Documentation pattern**: README.md / AGENT.md
- **Quality commands**: `TOOL --audit code`, `TOOL --lang audit`
- **Search commands**: `TOOL --search all`, `BRAIN recall`

Blueprints only override **storage concerns** (tiers, backends, features). The `load_blueprint()` function merges base rules underneath, so blueprint-specific values always take precedence.

## Interface

```python
from interface.brain import get_brain, load_blueprint, get_guidance_doc, audit_blueprint

brain = get_brain()
brain.store("working", "context", "# Current state...")
brain.search("provider bug", tier="knowledge")
brain.append("knowledge", "lessons", {"lesson": "...", "tool": "LLM"})

# Validate a blueprint
result = audit_blueprint("openclaw-20260316")
```

## Instances (Sessions)

Brain instances are isolated namespaces. Each instance has working memory, knowledge, and episodic data.

```bash
BRAIN session list                               # List instances
BRAIN session types                              # List available blueprints
BRAIN session create my-brain --type openclaw-20260316  # Create from blueprint
BRAIN session switch my-brain                    # Switch active instance
BRAIN session export my-brain                    # Export to zip
BRAIN session manifest                           # Regenerate MANIFEST.md
```

Agents should NOT switch instances autonomously. Switching is user-initiated.

## Adding a New Backend

1. Create `logic/brain/backends/<name>.py` implementing `BrainBackend`
2. Register in `logic/brain/loader.py::BACKEND_REGISTRY`
3. Reference in your blueprint: `"backend": "<name>"`
4. Test via `interface/brain.py` (never import from `logic/brain/` directly)

## Planned Backends

- **sqlite_fts**: SQLite FTS5 for full-text search
- **rag**: Vector embeddings (sentence-transformers + faiss)
- **hybrid**: flatfile + keyword + vector (inspired by OpenClaw)

## Tutorial

Full development guide: `logic/tutorial/brain/README.md`
Extensibility guide: `logic/tutorial/brain/extensibility.md`
