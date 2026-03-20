---
name: modularization
description: The supreme development principle. Decompose systems into layers, detect monolithic patterns, and maintain codebases that scale. Includes concrete anti-patterns from real development.
---

# Modularization

Modularization is the most important development practice in this ecosystem. Every system failure, every bug cluster, every developer frustration traces back to insufficient modularization. This skill defines what modularization means here and how to achieve it.

## The Rule

Every file, directory, and subsystem must have a single clear purpose. When a component grows beyond that purpose, decompose it. When components duplicate each other, unify them. When a flat list becomes hard to navigate, introduce hierarchy.

## Decomposition Signals

Refactor when you observe any of these:

| Signal | Symptom | Action |
|--------|---------|--------|
| **File too large** | >300 lines of logic in one file | Split by responsibility into subdirectory |
| **Function too long** | >50 lines doing multiple things | Extract sub-functions |
| **Flat directory** | >8 items at the same level with no grouping | Introduce subdirectories by category |
| **Feature pile-up** | Unrelated features in the same module | Separate into distinct modules |
| **Repeated patterns** | Same 5+ lines appearing in 3+ places | Extract into shared utility |
| **Missing interface** | External code reaches into internal implementation | Create `interface/main.py` facade |
| **Missing documentation** | Directory has code but no README.md or AGENT.md | Add navigation docs immediately |
| **Hard-coded assets** | URLs, paths, or resources embedded in logic | Move to config, data/, or resource files |

## The Three-Layer Architecture

Every command in this project follows the same layered decomposition:

```
Entry (main.py)          → Argument parsing, dispatch
Logic (logic/*.py)       → Business logic, no I/O formatting
Interface (interface/)   → Public API for cross-tool consumers
```

Violations of this pattern (e.g., logic mixed into main.py, direct cross-tool imports bypassing interfaces) create coupling that compounds over time.

## Case Study: The Assistant System

The assistant system's development history is a textbook example of what happens when modularization is neglected. The following issues were discovered during a 2026-03 audit:

### Provider/Model Directory Chaos

The LLM subsystem (`tool/LLM/logic/`) had models nested inside providers nested inside models. No `info.json` to record critical metadata like rate limits. No README.md or AGENT.md, so developers couldn't discover what each component did or how to use it. No interface layer, so the assistant GUI reached directly into provider internals.

**Lesson:** Every discrete component (a model, a provider, a tool) needs its own metadata file, its own documentation, and its own interface. The cost of adding these upfront is trivial compared to the cost of debugging an undocumented system.

### Frontend Monolith

The HTML GUI (`logic/_/assistant/gui/`) accumulated features without decomposition. CSS styles were duplicated across components instead of sharing a design system. Settings panels that already had working patterns for toggle switches were reimplemented with different CSS. The result: visual inconsistency, wasted development time, and brittle code.

**Lesson:** Before writing new UI code, search for existing patterns. The settings panel already has toggle styles? Use them. A chatbot blueprint exists? Extend it. Duplication in frontend code is just as harmful as in backend code.

### Missing Development Endpoints

During frontend development, there was no way to inspect the system's state from outside. No debug endpoints, no state viewers, no progress trackers. The developer believed the frontend worked because there were no errors — but the actual behavior was broken in ways that only a human user would notice.

**Lesson:** Build observability into every system from day one. Add status endpoints, state dumps, and health checks. If you can't inspect a running system programmatically, you cannot verify it works.

### Resource Management Failures

Model providers needed favicons/logos. Instead of downloading them in bulk from open-source repositories and storing locally, they were fetched at runtime via HTTP — degrading performance. When stored locally, naming was inconsistent (some `icon.png`, some `logo.svg`, some `favicon.ico`) instead of using a symmetric name like `logo.svg` everywhere.

**Lesson:** Centralize resource acquisition with a migration command (`TOOL --dev migrate`). Name resources symmetrically. Store them locally. Reference them by convention, not by hard-coded URL.

### No Database for Structured Data

Call records, session history, and rate-limit state were stored in flat files. This data is inherently structured and relational — it should be in a database (SQLite at minimum). Flat-file storage works for configuration and logs; it fails for queryable operational data.

**Lesson:** Match storage to data shape. Configuration → JSON/YAML files. Logs → append-only text. Structured records → database. Don't force relational data into flat files.

## Modularization Checklist

When reviewing or creating code, verify:

- [ ] No file exceeds 300 lines of logic (excluding tests and generated code)
- [ ] Every directory has README.md + AGENT.md
- [ ] Every cross-tool API goes through `interface/main.py`
- [ ] No duplicate implementations (run `TOOL --audit code` and search before creating)
- [ ] Flat directories with >8 entries are grouped into subdirectories
- [ ] Resources use symmetric naming conventions
- [ ] Hard-coded URLs/paths are moved to configuration
- [ ] Structured data uses appropriate storage (not flat files for relational data)
- [ ] New subsystems have observability (status endpoints, health checks)

## Detecting Dead Code

Dead code is the opposite of modularization — it's structure without purpose. Detect it with:

```bash
TOOL --audit code           # Finds unused imports, variables, syntax errors
TOOL --audit imports        # Finds import rule violations
TOOL --audit --lang --detect  # Finds hardcoded strings needing localization
```

When you find dead code: delete it. Don't comment it out. Version control preserves history.

## Handling Oversized Files

When a file grows too large:

1. Identify the distinct responsibilities within the file
2. Create a subdirectory with the same name as the file
3. Move each responsibility into its own file within the subdirectory
4. Create `__init__.py` that re-exports the public API
5. Update **all** callers directly (write a `tmp/batch_*.py` script for bulk updates)

Example: `logic/_/agent/command.py` (500+ lines) should become:

```
logic/_/agent/
├── command.py      # Dispatch only
├── session.py      # Session management
├── tools.py        # Tool execution
└── loop.py         # Main agent loop
```

## Bold Refactoring: No Backward Compatibility for Internal Code

When moving, renaming, or restructuring internal modules:

1. **Update all callers directly.** Don't create re-export shims, backward-compatibility wrappers, or "legacy location" aliases. Use `grep` to find every import, update them all, and delete the old path.
2. **Write a batch script** (`tmp/batch_rename_imports.py`) for changes touching 10+ files. This is faster and more reliable than manual edits.
3. **Delete dead paths immediately.** After migration, `rm -rf` the old directory. Never leave empty `__init__.py` files that re-export from the new location.
4. **Don't hedge with "deprecated" comments.** If code is moved, it's moved. The old location ceases to exist. Git preserves history for anyone who needs to understand the change.

### Why No Shims?

Backward-compat shims accumulate silently. Each one is "just one file" but collectively they:
- Create two valid import paths for the same code, confusing both humans and agents
- Silently fail when the target module changes its API
- Make dead code detection impossible (the shim looks "used" because callers import from it)
- Violate the single-responsibility principle at the module level

### Decision Rule

| Callers | Action |
|---------|--------|
| 0–5 | Update callers inline, delete old path |
| 6–20 | Write `tmp/batch_*.py` script, update all, delete old path |
| 20+ | Write batch script, update all, delete old path (no exceptions) |

There is **no threshold** at which backward compat becomes the right answer for internal code. External-facing APIs (published interfaces consumed by users or external tools) may warrant deprecation periods, but internal module reorganization never does.

### Real Example: logic/ Shim Cleanup (2026-03)

During the logic/ directory cleanup, six backward-compat shim directories were found (`logic/turing/`, `logic/mcp/`, `logic/accessibility/`, `logic/chrome/`, `logic/asset/`, `logic/serve/`) that each contained only an `__init__.py` re-exporting from `logic/utils/`. Total callers across all six: fewer than 10. Each shim was deleted and its callers updated directly. The cleanup took minutes and eliminated six phantom modules from the import namespace.

## Constructing Symmetric Systems

Symmetry reduces information entropy. When every tool directory has the same structure, an agent can navigate any tool without reading documentation first. See `skills/_/symmetric-design/SKILL.md` for the full treatment.
