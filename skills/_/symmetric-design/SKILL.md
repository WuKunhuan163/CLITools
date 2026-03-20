---
name: symmetric-design
description: Symmetric architecture principle — reduce information entropy through consistent structure, naming, and patterns across all system components.
---

# Symmetric Design

Symmetry is the architectural principle that makes this ecosystem navigable. When every tool has the same directory structure, every skill has the same format, and every command follows the same layered pattern, an agent can work across the entire codebase without reading documentation for each component.

## The Principle

**Information entropy decreases when structure is predictable.** If you've seen one tool directory, you know the shape of all tool directories. If you've read one `AGENT.md`, you know where to find guidance in any directory. This predictability is not accidental — it's designed.

## Symmetry Layers

### 1. Directory Symmetry

Every tool follows the same skeleton:

```
tool/<NAME>/
├── main.py            # Entry point
├── tool.json          # Metadata
├── logic/             # Business logic
├── interface/         # Public API (main.py)
├── hooks/             # Event-driven extensions
├── test/              # Tests
├── data/              # Persistent data (gitignored)
├── translation/       # Localization strings
├── README.md          # User documentation
└── AGENT.md       # Agent documentation
```

Root mirrors this: `logic/`, `interface/`, `hooks/`, `test/`, `data/`, `skills/`, `runtime/`.

When a new tool lacks any of these directories, it's incomplete — not by convention but by design. The skeleton is the API contract for discoverability.

### 2. Naming Symmetry

Consistent naming eliminates guesswork:

| Pattern | Rule | Example |
|---------|------|---------|
| Tool directories | UPPERCASE | `tool/GIT/`, `tool/PYTHON/` |
| Entry points | `main.py` | Every tool, every command |
| Interfaces | `interface/main.py` | Public API for cross-tool use |
| Metadata | `tool.json` | Tool configuration |
| User docs | `README.md` | Every directory |
| Agent docs | `AGENT.md` | Every directory |
| Resource files | `logo.svg` | Not `icon.png`, `favicon.ico`, etc. |
| Test files | `test_<module>.py` | Mirror the module being tested |

When naming resources, prefer a single canonical name. If every provider logo is `logo.svg`, you can construct the path `tool/<NAME>/data/logo.svg` without querying anything.

### 3. Command Symmetry

Every symmetric command (`--audit`, `--dev`, `--eco`, `--list`) inherits from `EcoCommand` and follows the same dispatch pattern:

```python
class AuditCommand(EcoCommand):
    name = "audit"
    def handle(self, args): ...
```

This means every command can be found in `logic/_/<name>/command.py`, tested the same way, and extended the same way.

### 4. Documentation Symmetry

Every directory has three potential documentation layers:

| File | Audience | Purpose |
|------|----------|---------|
| `README.md` | Humans | What this is, how to use it |
| `AGENT.md` | Agents | How to work with it, what to watch for |
Not every directory needs both. But when they exist, their role is predictable. Self-improvement gaps are tracked centrally in `runtime/_/eco/brain/tasks.md`.

### 5. Skills Symmetry

Skills are organized as a dictionary tree. Each directory level has:
- `README.md` — What you'll find here
- `AGENT.md` — Navigation guide (what's below, what's above)
- Subdirectories — each containing either more subdirectories or a `SKILL.md`

This makes skills browsable by hierarchy, searchable by name, and navigable by agents who don't know the exact skill they need.

## Entropy Reduction in Practice

### Before Symmetric Design

```
tool/LLM/data/
├── openai_icon.png
├── anthropic-logo.svg
├── google_favicon.ico
├── zhipu.jpg
```

An agent seeing this must inspect each file to understand the naming convention. The entropy is high — four different patterns for the same concept.

### After Symmetric Design

```
tool/LLM/data/
├── openai/logo.svg
├── anthropic/logo.svg
├── google/logo.svg
├── zhipu/logo.svg
```

Zero entropy in naming. The path is constructable: `data/{provider}/logo.svg`.

## When to Break Symmetry

Symmetry is a strong default, not an absolute rule. Break it when:

- A component genuinely has no equivalent in the standard skeleton (e.g., a tool with no public interface because it's purely internal)
- The symmetric structure would create empty, misleading directories
- Performance requires a non-standard layout

When breaking symmetry, document why in `AGENT.md`.

## Audit

Run `TOOL --audit quality` to detect structural asymmetries:
- Missing `interface/main.py` when `logic/` exists
- Missing documentation files
- Inconsistent hook configurations

The audit system itself follows symmetric design — each audit phase uses the same input/output patterns, making the full-flow audit possible.
