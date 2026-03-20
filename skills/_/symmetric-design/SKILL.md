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

Root mirrors this: `logic/`, `interface/`, `hooks/`, `test/`, `data/`, `skills/`, `data/_/runtime/`.

**logic/ Module Rule:** The root `logic/` directory has exactly two categories of subdirectories:

1. **`logic/_/`** — Shared infrastructure (config, agent, setup, hooks, utils, gui, etc.)
2. **`logic/<COMMAND>/`** — Command-specific shared logic, where `<COMMAND>` matches an installed tool command in `bin/`. Examples: `logic/brain/` (matches `bin/BRAIN`), `logic/git/` (matches `bin/GIT`), `logic/tool/` (matches `bin/TOOL`).

Nothing else is allowed at the `logic/` level except `__init__.py` and documentation. If a module is shared infrastructure (used by multiple tools, not command-specific), it belongs in `logic/_/`. If it's command-specific shared logic for a tool that's invoked as `TOOL_NAME "xxx"` (no sub-commands), it can go in `logic/<command>/main.py`.

When a new tool lacks any of these directories, it's incomplete — not by convention but by design. The skeleton is the API contract for discoverability.

#### main.py vs cli.py: The Command Lifecycle

These two filenames have distinct semantic roles in the command dispatch lifecycle:

| File | Role | Location | Lifecycle Position |
|------|------|----------|-------------------|
| `main.py` | **Start** of command processing | Tool root (`tool/<NAME>/main.py`) | Entry point — inherits base, launches argparse |
| `cli.py` | **End** of command processing | Deep in `logic/` tree (`logic/_/<cmd>/cli.py`) | Concrete endpoint — application logic |

**Why not rename all to `cli.py`?** `main.py` invokes the base tool's argparse blueprint, which auto-discovers routes by traversing the project's `logic/_/` (shared eco commands) and the tool's `logic/` (hierarchical commands). Each `cli.py` is the final destination where a specific command is actually handled.

**Stateless base argparse:** The base tool's argparse is **stateless** — the directory structure itself IS the routing state. `main.py` doesn't need to declare which commands exist; it just inherits from `ToolBase` and calls `handle_command_line()`. The base discovers available commands by checking which directories have `cli.py` files.

This means `main.py` should be **minimal**:

```python
from interface.tool import ToolBase
tool = ToolBase("MY_TOOL")
parser = argparse.ArgumentParser(prog="MY_TOOL", add_help=False)
if tool.handle_command_line(parser):
    return
```

**Decomposition rule:** If `main.py` contains non-trivial application logic beyond argparse setup, that logic should be decomposed into `cli.py` endpoints under `logic/`. The presence of business logic in `main.py` is a signal that the command tree needs deeper modularization.

**Cross-referencing in cli.py:** Each `cli.py` endpoint can:
- Import from `interface/` for cross-tool APIs
- Access peer `cli.py` files via the tool's own `logic/` directory
- Use the `EcoCommand` base class for shared formatting/utilities

**Scaffold:** Use `TOOL ---dev scaffold <tool_name> <command/path>` to create new entry point directories with `cli.py`, `README.md`, and `AGENT.md` templates.

### 2. Naming Symmetry

Consistent naming eliminates guesswork:

| Pattern | Rule | Example |
|---------|------|---------|
| Tool directories | UPPERCASE | `tool/GIT/`, `tool/PYTHON/` |
| Tool entry points | `main.py` | Starts argparse routing |
| Command endpoints | `cli.py` | Handles a specific command |
| Interfaces | `interface/main.py` | Public API for cross-tool use |
| Metadata | `tool.json` | Tool configuration |
| User docs | `README.md` | Every directory |
| Agent docs | `AGENT.md` | Every directory |
| Resource files | `logo.svg` | Not `icon.png`, `favicon.ico`, etc. |
| Test files | `test_<module>.py` | Mirror the module being tested |

When naming resources, prefer a single canonical name. If every provider logo is `logo.svg`, you can construct the path `tool/<NAME>/data/logo.svg` without querying anything.

### 3. Command Symmetry

Commands follow a **three-tier classification** based on their role in the ecosystem. Each tier has a distinct indicator pattern, implementation location, and dispatch mechanism.

#### Tier 1: Shared Eco Commands (prefix: `---`)

Framework-level commands available to **all tools**. Their implementation lives in `logic/_/<name>/cli.py`. They are intercepted in `handle_command_line()` before tool-specific argparse runs.

| Command | Implementation | Purpose |
|---------|---------------|---------|
| `---dev` | `logic/_/dev/cli.py` | Development utilities |
| `---test` | `logic/_/test/manager.py` | Test runner |
| `---setup` | `logic/_/setup/engine.py` | Tool installation |
| `---config` | `logic/_/config/` | Configuration |
| `---eco` | `logic/_/eco/navigation.py` | Ecosystem navigation |
| `---skills` | `logic/_/skills/cli.py` | Skill management |
| `---hooks` | `logic/_/hooks/` | Hook management |
| `---audit` | `logic/_/audit/cli.py` | Code quality |
| `---assistant` | `logic/_/assistant/` | Agent sessions |
| `---agent` / `---ask` / `---plan` | `logic/_/agent/cli.py` | Agent modes |
| `---install` / `---uninstall` | `logic/_/setup/` | Subtool management |
| `---rule` | `logic/_/setup/` | Rule display |

**Key rule:** If a command is shared (appears in `base.py`'s dispatch), its logic MUST be in `logic/_/`. Conversely, if logic is in `logic/_/`, it should be reachable via a shared `---command`.

**Unordered dispatch:** Eco tokens are resolved by finding the registered handler among all `---` tokens in argv. Order does not matter: `TOOL ---dev ---create` and `TOOL ---create ---dev` are equivalent — the system finds `---dev` as the primary handler and passes `create` as a sub-argument. This reduces cognitive load for users.

#### Tier 2: Hierarchical Commands (tool-specific subparsers)

Tool-specific commands whose argparse structure **mirrors the directory structure** in `tool/<NAME>/logic/`. Each subcommand level corresponds to a directory level:

```
TOOL_NAME subcmd1 subcmd2 action args
    └─→ tool/<NAME>/logic/subcmd1/subcmd2/main.py → handle_action(args)
```

Example: `LLM provider add openai` → `tool/LLM/logic/provider/add/main.py` or `tool/LLM/logic/provider/engine.py:handle_add()`.

**Implementation:** Use `argparse.add_subparsers()` hierarchically. Each `logic/` subdirectory with a `main.py` or `__init__.py` becomes a potential subparser level. The convention ensures:
- `README.md` at each `logic/` subdirectory guides users
- `AGENT.md` at each level guides agents navigating the command tree
- Terminal `main.py` files contain the actual command handler

#### Tier 3: Decorator Commands (modifiers, prefix: `-`)

Flags that modify the behavior of other commands without producing their own dispatch. They are stripped from `sys.argv` before dispatch.

| Decorator | Effect |
|-----------|--------|
| `-no-warning` | Suppress warning output |
| `-tool-quiet` | Minimize all output |
| `--mcp-*` | Rewrite to bare subcommand for MCP |

**Indicator:** Decorators use single-dash long flags (`-no-warning`, `-tool-quiet`). They NEVER have subcommands of their own and are always `action="store_true"` boolean flags. In argparse definitions, always list the `-` form first: `add_argument("-no-warning", "--no-warning", ...)`.

#### Dispatch Order

The dispatch follows a strict precedence:
1. **Decorators** (`-flag`) are stripped from `sys.argv`
2. **Shared eco commands** (`---flag`) are collected, handler resolved by matching against registry (unordered)
3. **Subtool delegation** checks for `tool/<NAME>/tool/<CMD>/main.py`
4. **Hierarchical commands** (`--flag` or positional) fall through to tool's own argparse

#### Dash-Level Indicators (argparse-native)

argparse natively supports different dash counts as distinct option prefixes. This gives **syntactic indicators** for command tiers:

| Tier | Syntax | argparse | Example |
|------|--------|----------|---------|
| Shared eco | `---<name>` (triple dash) | `add_argument('---dev', ...)` | `TOOL ---dev info` |
| Hierarchical | `--<name>` or positional | `add_argument('--provider', ...)` or subparsers | `LLM --provider add` |
| Decorator | `-<name>` (single dash, long) | `add_argument('-no-warning', ...)` | `TOOL -no-warning` |
| Positional | `<value>` (no dash) | Positional args | `TOOL "query text"` |

Tiers are **syntactically unambiguous** — `---dev`, `--dev`, and `-dev` are three distinct options. No naming collisions possible.

#### Implementation

The base tool at `logic/base/blueprint/base.py` handles all three tiers in `handle_command_line()`:

1. Decorators (`-*`) stripped from `sys.argv`
2. All `---` tokens collected into a list; the registered handler is found (unordered)
3. Remaining positional args plus unused eco tokens are passed to the handler
4. If no eco token matched, hierarchical command dispatch via tool's argparse

#### Conformance Audit

Run `TOOL ---audit argparse` to verify all tools comply with the three-tier convention. Run `TOOL ---audit argparse --fix` to auto-fix decorator prefix issues and auto-create missing `logic/_/` directories for eco commands.

#### Refactor Aggressiveness

The global config `refactor_aggressiveness` (set via `TOOL ---config set refactor_aggressiveness <0|1>`) controls how agents approach refactoring:

| Value | Behavior |
|-------|----------|
| `0` | Conservative: preserve backward compat, add shims, gradual migration |
| `1` | Bold: no backward compat, no shims, no legacy fallbacks. Clean break. |

**Default is `1`.** The ecosystem philosophy: when few callers are affected, remove old code immediately. Long-term maintenance cost of shims always exceeds the short-term pain of a clean refactor. See also: `modularization` skill's "Bold Refactoring" section.

### 4. Documentation Symmetry

Every directory has three potential documentation layers:

| File | Audience | Purpose |
|------|----------|---------|
| `README.md` | Humans | What this is, how to use it |
| `AGENT.md` | Agents | How to work with it, what to watch for |
Not every directory needs both. But when they exist, their role is predictable. Self-improvement gaps are tracked centrally in `data/_/runtime/_/eco/brain/tasks.md`.

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

### 6. Non-CLI Content Symmetry

Non-CLI content (web frontends, HTML GUIs, static assets, configuration templates) follows the same modular principle as CLI commands: **store alongside the command that manages it.**

| Content Type | Location | Managed By |
|-------------|----------|------------|
| HTML GUI | `tool/<NAME>/logic/<feature>/gui/` | The feature's command handler |
| Web frontend | `logic/_/assistant/gui/` | `--assistant` shared command |
| Static assets | `tool/<NAME>/data/` or `logic/_/utils/asset/` | Setup/migration |
| Config templates | `logic/_/setup/IDE/<ide>/` | `--setup` command |
| Report output | `report/<namespace>/` | `--report` command |

**Rule:** Every non-CLI file should be reachable from its managing command's "relative directory." If `--assistant` manages the web GUI, the GUI lives in `logic/_/assistant/gui/`. If `tool/LLM` has a configuration wizard, it lives in `tool/LLM/logic/setup/gui/`. This shares information entropy with the CLI hierarchy — you don't need a separate mental model for where non-CLI files live.

**Path Construction:** Given a command path, the non-CLI content path is constructable:
- Shared eco command `--X` → non-CLI content in `logic/_/X/gui/` or `logic/_/X/static/`
- Tool command `TOOL sub` → non-CLI content in `tool/TOOL/logic/sub/gui/`
- Assets shared across tools → `logic/_/utils/asset/`

### 7. Data Symmetry

User data follows path correspondence with code:

| Code Location | Data Location | Purpose |
|--------------|---------------|---------|
| `logic/_/eco/` | `data/_/eco/` | Ecosystem state |
| `logic/_/audit/` | `data/_/audit/` | Audit caches/results |
| `logic/_/assistant/` | `data/_/assistant/` | Session data |
| `logic/brain/` | `data/_/runtime/brain/` | Brain working state |
| `tool/<NAME>/logic/` | `tool/<NAME>/data/` | Tool-specific data |

**Rule:** Runtime/user data ALWAYS lives under `data/` (gitignored by default). Code NEVER writes to `logic/` or root directories for data storage. If you see `runtime/` or `workspace/` at root level, it's a migration bug — the canonical location is `data/_/runtime/` and `data/_/workspace/`.

## When to Break Symmetry

Symmetry is a strong default, not an absolute rule. Break it when:

- A component genuinely has no equivalent in the standard skeleton (e.g., a tool with no public interface because it's purely internal)
- The symmetric structure would create empty, misleading directories
- Performance requires a non-standard layout

When breaking symmetry, document why in `AGENT.md`.

## Audit

Run `TOOL ---audit quality` to detect structural asymmetries:
- Missing `interface/main.py` when `logic/` exists
- Missing documentation files
- Inconsistent hook configurations

Run `TOOL ---audit argparse` to check three-tier dash convention compliance. Use `--fix` to auto-remediate.

The audit system itself follows symmetric design — each audit phase uses the same input/output patterns, making the full-flow audit possible.

## Information Entropy Quantification

The entropy audit (`TOOL ---audit entropy`) quantifies structural predictability across 6 dimensions:

| Dimension | What It Measures | Metric |
|-----------|-----------------|--------|
| Directory Structure | Tool skeleton consistency | % of tools missing canonical items |
| Naming | Casing/file naming patterns | Shannon entropy of naming patterns |
| Path Correspondence | Code ↔ data mirroring | % of logic/_/ modules with data/_/ mirrors |
| Module Coherence | logic/ dirs match bin/ commands | Violation count |
| Sibling Balance | Even-sized peer directories | Coefficient of variation |
| Import Graph | Interface usage vs direct logic/ | Bypass ratio |

**Interpretation scale:** 0.0 = perfectly predictable, 1.0 = maximum chaos.

| Score | Grade | Meaning |
|-------|-------|---------|
| 0.00-0.15 | Excellent | Knowing one part predicts the rest |
| 0.15-0.30 | Good | Minor inconsistencies |
| 0.30-0.50 | Moderate | Needs attention |
| 0.50-0.70 | Poor | Significant disorganization |
| 0.70-1.00 | Critical | Restructuring needed |

The entropy audit protocol outputs JSON following a standardized envelope format (version, timestamp, connections, suggestions), enabling trend tracking across audit runs and CI/CD integration.
