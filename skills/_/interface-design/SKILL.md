---
name: interface-design
description: When and how to extract interfaces from internal logic. Covers anti-patterns that signal interface extraction is needed, the facade layer pattern, and interface documentation standards.
---

# Interface Design

Interfaces are the contracts between modules. In this ecosystem, every tool's public API lives in `interface/main.py` — a thin facade over `logic/` internals. The root `interface/` directory provides cross-tool shared facades. This skill teaches you to recognize when code needs interface extraction and how to do it correctly.

## Why Interfaces Matter

Without interfaces:
- Tools import directly from each other's `logic/` directories, creating tight coupling.
- Refactoring one tool's internals breaks every consumer.
- New agents have no discoverable entry point — they must read implementation to learn the API.
- `TOOL --audit imports` (IMP001) flags violations, but prevention is better than detection.

## When to Extract an Interface

### Signal 1: Cross-Tool Logic Import

**Symptom**: `from tool.X.logic.engine import some_function` in another tool.

**Fix**: Add `some_function` to `tool/X/interface/main.py` with documentation. The consumer imports `from tool.X.interface.main import some_function`. Declare the dependency in the consumer's `tool.json`.

**Real example**: `logic/utils/chrome/` contained Chrome CDP session management used by 8+ tools (GOOGLE, CLOUDFLARE, ASANA, ATLASSIAN, etc.). Instead of each tool importing `from logic.utils.chrome.session import ChromeSession`, the CDMCP tool exposes `from tool.GOOGLE.CDMCP.interface.main import boot_session, require_tab`.

### Signal 2: Tool Implementing Another Tool's Functionality

**Symptom**: Tool A contains code that logically belongs to Tool B (e.g., the OPENCLAW tool had Chrome automation code that belongs in CDMCP).

**Fix**: Move the logic to the correct tool, expose it via interface, and have the original tool import from the interface. This prevents functionality from scattering across tools.

**Real example**: Chrome keyboard detection was in `logic/accessibility/` (a shared utility), but it's actually a GOOGLE.GC concern. The correct design: GOOGLE.GC owns the keyboard detection logic in its `logic/`, exposes it via `interface/`, and `interface/accessibility.py` delegates to it.

### Signal 3: Too Much Implementation in Interface

**Symptom**: `interface/main.py` contains business logic, data transformations, or complex orchestration instead of thin delegation.

**Fix**: Interface files should contain:
- Import and re-export of functions from `logic/`
- Type annotations and docstrings
- Thin wrappers that add minimal coordination (e.g., default parameter injection)

They should NOT contain:
- Data processing, validation, or transformation logic
- Direct file I/O or network calls
- Multi-step orchestration (that belongs in `logic/`)

### Signal 4: Missing Interface for Shared Logic

**Symptom**: Multiple tools duplicate the same utility function instead of importing a shared one.

**Fix**: Create or extend a shared interface in `interface/`. The implementation lives in `logic/utils/` or a dedicated `logic/` submodule.

## Interface Documentation Standards

An interface's documentation (in its AGENT.md and README.md) must cover:

| Section | Purpose | Example |
|---------|---------|---------|
| **What it does** | One-line summary | "Chrome CDP session management for browser automation tools" |
| **Input/Output** | Function signatures with types | `boot_session(url: str, timeout: int = 30) -> Session` |
| **Error conditions** | What exceptions can be raised | "Raises `SessionTimeout` if Chrome doesn't respond within `timeout`" |
| **Side effects** | Non-obvious behaviors | "Creates a Chrome profile directory in `data/chrome/profiles/`" |
| **Related interfaces** | Upstream and downstream | "Consumers: ASANA, CLOUDFLARE. Depends on: GOOGLE.GC interface" |

### Interface Change Propagation

When modifying an interface:
1. Update the interface's own AGENT.md and README.md
2. Search for all consumers: `TOOL --audit imports --tool <NAME>`
3. Update every consumer's documentation if the change affects their behavior
4. Propagate until no further downstream impact exists

## The `TOOL --audit imports` Check

The audit system enforces interface boundaries:

| Code | Rule | Severity |
|------|------|----------|
| IMP001 | No direct `logic/` imports across tools | Error |
| IMP002 | Interface functions must be documented | Warning |
| IMP003 | Dependencies must be declared in `tool.json` | Error |
| IMP004 | Unused interface exports | Warning |

Run `TOOL --audit imports` before committing cross-tool changes.

## Blueprint-Instance Pattern

For systems that have both a template (source of truth) and a deployed version (runtime instance), use the blueprint-instance pattern with a CLI bridge:

| Concept | Location | Example |
|---------|----------|---------|
| **Blueprint** | Deep in `logic/_/` | `logic/_/setup/IDE/cursor/rules/*.mdc`, `logic/_/hooks/IDE/Cursor/` |
| **Instance** | Shallow, IDE-accessible | `.cursor/rules/*.mdc`, `.cursor/hooks.json` |
| **CLI bridge** | Deploy command | `TOOL --setup`, `logic/_/setup/IDE/cursor/deploy.py` |

### When to Use This Pattern

- Configuration templates that are deployed to IDE-specific locations
- Hook scripts that have a source version and a deployed reference
- GUI blueprints that generate runtime HTML/config
- Any system where the source of truth should be version-controlled but the runtime needs a different path

### Real Example: Hooks Decomposition (2026-03-18)

Root `hooks/` directory contained Cursor IDE hook scripts. These were moved to `logic/_/hooks/IDE/Cursor/` (blueprint). The `.cursor/hooks.json` (instance) references these scripts by path. The deploy script syncs blueprint → instance.

Before: `hooks/instance/IDE/Cursor/brain_inject.py` (root-level, mixing concerns)
After: `logic/_/hooks/IDE/Cursor/brain_inject.py` (organized in logic, blueprint is source of truth)

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | Fix |
|-------------|---------------|-----|
| `from tool.X.logic.engine import func` | Bypasses interface contract | Import from `tool.X.interface.main` |
| 500-line `interface/main.py` | Interface is doing too much | Move logic to `logic/`, keep interface thin |
| Tool A implements Tool B's feature | Functionality scattering | Migrate to Tool B, expose interface |
| Duplicating a utility in 3 tools | No shared interface | Create `interface/` facade over `logic/utils/` |
| Interface with no docstrings | Consumers can't discover API | Add type hints, docstrings, AGENT.md |
| Changing interface without updating consumers | Silent breakage | Run `--audit imports`, update downstream docs |
| Blueprint and instance diverging | Stale deployments | Always deploy via CLI bridge, never edit instances directly |
