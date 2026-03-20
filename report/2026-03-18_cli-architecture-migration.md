# CLI Architecture Migration Report

**Date**: 2026-03-18  
**Scope**: logic/ migration, ---brain eco command, ---help system, documentation update

## Completed Changes

### 1. Legacy Directory Cleanup

Removed `logic/base/`, `logic/brain/`, `logic/git/`, `logic/tool/` — all were redundant copies of code already migrated to `logic/_/`. No Python imports referenced the legacy locations.

**Before**: `logic/` had both `logic/_/base/` and `logic/base/` (confusing duplication)  
**After**: Single source of truth in `logic/_/`

### 2. BRAIN → ---brain Eco Command

BRAIN is ecosystem infrastructure, not a standalone tool. Converted from monolithic `bin/BRAIN` (750 lines) to `logic/_/brain/cli.py` (EcoCommand subclass).

- `TOOL ---brain list/add/done/status/...` — eco command
- `bin/BRAIN` — backward-compatible shorthand (delegates to eco command)
- Brain data remains in `data/_/runtime/_/eco/brain/`

### 3. ---help Eco Command

Created `logic/_/help/cli.py` — generates help from DFS traversal of `argparse.json` files across all `logic/_/` directories.

- Shows full command tree with descriptions
- Supports filtering: `TOOL ---help audit`
- Machine-readable: `TOOL ---help --json`
- Created `argparse.json` for all eco commands

### 4. USERINPUT No-Args Fix

USERINPUT with no arguments now opens the GUI (default behavior) instead of showing argparse help. The fix bypasses `ToolBase.handle_command_line()` for the no-args case.

### 5. Documentation Updated

- `logic/README.md` — reflects post-migration single-tier architecture
- `logic/AGENT.md` — updated with command map rule, three-tier convention, __/ convention
- `logic/_/base/AGENT.md` — CliEndpoint pattern, __/ co-located data rules
- `logic/_/help/AGENT.md` — help system internals
- Root `AGENT.md` — updated command references from `BRAIN` to `TOOL ---brain`

## Architectural Concepts

### Three-Tier CLI Convention

```
---<name>    Eco commands (logic/_/<name>/cli.py)     shared across all tools
--<name>     Tool commands (argparse in main.py)       tool-specific
-<name>      Decorators (-no-warning, -tool-quiet)     behavioral modifiers
```

### Command Map Rule

Each `logic/_/<name>/` directory with `cli.py` automatically maps to `---<name>`. The directory structure IS the routing state. No registration needed.

### argparse.json as Declarative Schema

Every command directory should have `argparse.json` that declares:
- Name and description
- Subcommands with their descriptions and args
- This powers `---help` tree generation AND audit verification

### __/ Co-Located Data Convention

Endpoint directories may contain `__/` for tightly-coupled data:
- Test fixtures, templates, schemas
- Only the parent endpoint may reference `__/`
- No business logic in `__/`
- Auditable: `TOOL ---audit` checks referential integrity

### Hierarchical User Data (Concept)

The `logic/_/` hierarchy maps commands. A parallel hierarchy can map **user data**:

| Command hierarchy | User data hierarchy |
|---|---|
| `logic/_/brain/cli.py` | `data/_/brain/` |
| `logic/_/audit/cli.py` | `data/_/audit/` (cache) |
| `logic/_/dev/cli.py` | `data/_/dev/` (archived tools) |

Root-level data directories (`report/`, `skills/`, `migrate/`) already follow this pattern informally. The concept extends it:

- `report/` is the user data for `---dev` or a future `---report` command
- `skills/` is the user data for `---skills` command
- `migrate/` is the user data for `---migrate` command

This parallel makes both command endpoints and their data auditable as a pair.

### Full-Path Testing (Concept)

Each leaf `cli.py` endpoint should have at least one test that invokes through the full chain: `bin/TOOL → ToolBase.handle_command_line() → directory traversal → cli.py.dispatch(ctx)`.

The `argparse.json` schema enables auto-generation of smoke tests:
1. Read `argparse.json` for each endpoint
2. Generate a test that invokes `TOOL ---<name>` with `--help` or no args
3. Verify exit code 0 and non-empty output

This replaces manual test_00_help.py boilerplate with schema-driven generation.

## Session 2 Additions

### 6. USERINPUT CLI Decomposition

Refactored USERINPUT from a monolithic 1258-line `main.py` into a hierarchical structure:

```
tool/USERINPUT/
├── main.py              ← Thin router (160 lines, down from 1258)
├── logic/
│   ├── __init__.py      ← Shared utilities (get_config, get_msg, exceptions)
│   ├── cli.py           ← Root entry: GUI feedback collection
│   ├── argparse.json    ← Root schema
│   ├── queue/
│   │   ├── store.py     ← Queue FIFO storage (moved from queue.py)
│   │   ├── cli.py       ← --queue subcommand dispatch
│   │   └── argparse.json
│   ├── prompt/
│   │   ├── cli.py       ← --system-prompt subcommand dispatch
│   │   └── argparse.json
│   └── config/
│       ├── cli.py       ← --config + --enquiry-mode dispatch
│       └── argparse.json
```

All 27 existing tests pass. CLI interface unchanged (backwards compatible).

### 7. `__/` Co-Located Data Audit

Added `TOOL ---audit colocated` command that verifies:
- `__/` dirs only exist alongside cli.py or main.py
- No business logic (class/def) in `__/`
- External code doesn't reference `__/` contents

### 8. Full-Path Endpoint Smoke Tests

Added `TOOL ---audit endpoints` that:
- Discovers all eco commands via argparse.json
- Invokes `TOOL ---<name> --help` through the full dispatch chain
- Reports pass/fail/skip status
- Result: 12/12 testable endpoints pass, 5 skipped (interactive)

### 9. Parallel Hierarchy Documentation

Documented the command-to-data mapping pattern:
- `logic/_/<name>/cli.py` ↔ `data/_/<name>/`
- Root directories (`report/`, `skills/`, `migrate/`) follow the same pattern
- Updated in root `AGENT.md` and `logic/AGENT.md`
