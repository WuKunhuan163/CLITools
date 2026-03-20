# Brain Blueprint Development Guide

How to create, validate, and deploy brain blueprints for the AITerminalTools agent ecosystem.

## What is a Brain Blueprint?

A **blueprint** defines how an AI agent stores, retrieves, and manages knowledge. It specifies:
- **Tiers**: independent memory layers (working, knowledge, episodic)
- **Backends**: storage engines per tier (flatfile, SQLite FTS, vector DB, custom)
- **Instance structure**: directory layout when a brain instance is created
- **Context injection**: how and when brain data is injected into agent context
- **Hooks**: lifecycle events (session start, tool use, stop)

Blueprints live in `logic/brain/blueprint/<name>/`. Brain **instances** (runtime data) live in `runtime/brain/sessions/<name>/`.

## Quick Start

```bash
# 1. Create a blueprint directory
mkdir -p logic/brain/blueprint/my-brain-20260316

# 2. Write blueprint.json (see specification below)

# 3. Add README.md (required for discoverability)

# 4. Validate
python3 -c "from interface.brain import audit_blueprint; print(audit_blueprint('my-brain-20260316'))"

# 5. Create an instance
BRAIN session create test --type my-brain-20260316
```

## Directory Structure

```
logic/brain/
├── blueprint/                    # Blueprint definitions (tracked in git)
│   ├── base.json                 # Shared ecosystem rules (all blueprints inherit)
│   ├── README.md                 # Blueprint index
│   ├── clitools-20260316/        # Default: file-based, zero dependencies
│   │   ├── blueprint.json
│   │   ├── README.md
│   │   └── defaults/SOUL.md      # Default personality
│   ├── claude-mem-20260316/      # L0/L1/L2 context compression
│   │   ├── blueprint.json
│   │   └── README.md
│   └── rag-20260316/             # Vector embeddings (planned)
│       ├── blueprint.json
│       └── README.md
├── instance/                     # Instance management logic
│   ├── session.py                # BrainSessionManager
│   └── __init__.py
├── utils/                        # Audit and validation
│   ├── audit.py                  # Blueprint auditor
│   └── __init__.py
├── backends/                     # Storage engine implementations
│   └── flatfile.py               # Reference implementation
├── base.py                       # Abstract BrainBackend interface
└── loader.py                     # Blueprint loader + merger
```

## Blueprint Specification

### Naming Convention

```
<type>-<YYYYMMDD>
```

The date suffix enables versioning while preserving older versions for compatibility.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Must match directory name |
| `version` | string | Semantic version (e.g., "1.0") |
| `inherits` | string | Must be `"base"` to inherit ecosystem rules |
| `description` | string | One-line description |
| `tiers` | object | Tier definitions (see below) |

### Tier Definition

Each tier is a named memory layer with its own storage config:

```json
{
  "tiers": {
    "working": {
      "description": "Hot state: current session tasks, context, activity.",
      "backend": "flatfile",
      "relative_path": "working/",
      "files": {
        "context": "context.md",
        "tasks": "tasks.json",
        "activity": "activity.jsonl"
      },
      "lifecycle": "session",
      "inject_at": "sessionStart"
    }
  }
}
```

| Tier Field | Required | Values |
|------------|----------|--------|
| `backend` | Yes | Registered backend name (e.g., `"flatfile"`, `"rag"`) |
| `relative_path` | Yes | Path relative to instance root (MUST NOT contain `..` or absolute paths) |
| `files` | Yes | Map of logical names to file paths within the tier |
| `lifecycle` | No | `"session"` (reset per session) or `"permanent"` (persists) |
| `inject_at` | No | `"sessionStart"`, `"on_demand"`, `"postToolUse"`, `"never"` |
| `description` | No | Human-readable description |

### Path Safety Rules

**Critical**: paths in blueprints MUST be relative and contained within the instance directory.

- `relative_path` MUST NOT start with `/` (no absolute paths)
- `relative_path` MUST NOT contain `..` (no parent directory traversal)
- `relative_path` MUST NOT contain `~`, `/etc`, `/usr`, `/tmp`, or other system paths
- File paths in `files` MUST NOT escape their tier's `relative_path`

The audit tool (`logic/brain/utils/audit.py`) simulates path resolution and will flag violations.

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `sessions` | object | Session management config (`enabled`, `manifest_file`) |
| `features` | object | Type-specific capabilities |
| `dependencies` | object | External packages needed (`pip` array, `note` string) |
| `context_injection` | object | How brain data is injected into agent context (see extensibility) |

## base.json — Shared Ecosystem Rules

All blueprints inherit from `logic/brain/blueprint/base.json`, which defines:

- **guidance**: bootstrap docs, reflection protocol, onboarding skill, BRAIN commands
- **hooks**: IDE integration (sessionStart, postToolUse, stop)
- **directory_conventions**: tracked vs. gitignored symmetric directories
- **documentation**: per-directory doc pattern (README/for_agent/for_agent_reflection)
- **quality_commands**: code audit and language audit commands
- **search_commands**: semantic and keyword search commands

Blueprint-specific values **override** base values. Merging uses shallow dict merge (type wins on conflict).

## Validation

Always validate before deploying:

```python
from interface.brain import audit_blueprint

result = audit_blueprint("my-brain-20260316")
if not result["passed"]:
    for error in result["errors"]:
        print(f"ERROR: {error}")
```

The auditor checks:
1. Required fields present
2. Path safety (no escape, no absolute, no dangerous patterns)
3. Backend registration (declared backends exist in BACKEND_REGISTRY)
4. Inheritance validity (base.json exists if `inherits: "base"`)
5. Documentation presence (README.md)
6. Instance creation simulation (path conflicts, tier overlaps)

## Adding a New Backend

1. Implement `logic/brain/backends/<name>.py` extending `BrainBackend`:
   ```python
   from logic.brain.base import BrainBackend
   
   class MyBackend(BrainBackend):
       def store(self, tier, key, value): ...
       def retrieve(self, tier, key): ...
       def search(self, query, tier=None): ...
       def append(self, tier, key, entry): ...
       def list_keys(self, tier): ...
   ```

2. Register in `logic/brain/loader.py`:
   ```python
   BACKEND_REGISTRY["my_backend"] = "logic.brain.backends.my_backend.MyBackend"
   ```

3. Reference in your blueprint:
   ```json
   { "tiers": { "knowledge": { "backend": "my_backend" } } }
   ```

## Defaults Directory

Blueprints can include a `defaults/` directory with files copied into new instances:

```
my-brain-20260316/
├── blueprint.json
├── README.md
└── defaults/
    ├── SOUL.md          # Default personality
    ├── MEMORY.md        # Pre-loaded memories
    └── prompts/         # Custom prompt templates
```

## Checklist for New Blueprints

- [ ] Directory: `logic/brain/blueprint/<name>-<YYYYMMDD>/`
- [ ] `blueprint.json` with all required fields
- [ ] `"inherits": "base"` set
- [ ] All paths are relative, no `..` or absolute paths
- [ ] Declared backends exist in BACKEND_REGISTRY (or documented as planned)
- [ ] `README.md` describing philosophy and use cases
- [ ] `defaults/` directory if the blueprint needs pre-loaded data
- [ ] Audit passes: `audit_blueprint("<name>")` returns `passed: True`
- [ ] Dependencies documented if external packages are needed

## Advanced: Extensibility

For multi-language backends, complex triggers, and interface extensions, see [extensibility.md](extensibility.md).
