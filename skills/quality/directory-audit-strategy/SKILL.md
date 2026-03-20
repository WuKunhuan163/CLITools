---
name: directory-audit-strategy
description: Systematic approach to auditing directory structures in symmetric root directories. Covers irregularity detection, naming conventions, documentation requirements, and extensibility patterns.
---

# Directory Audit Strategy

## Purpose

Detect and fix structural irregularities in symmetric root directories. Every directory should be self-documenting, internally consistent, and follow the project's symmetric design pattern.

## Audit Checklist

### 1. Structural Regularity

**Rule**: Siblings at the same level should serve the same role.

- **Bad**: A blueprint directory where most children are blueprint implementations, but one child is a utility module.
- **Good**: All children are blueprints; utilities live in a shared `utils.py` or `common/` at the same level.

Check:
- List all items at each level. Do they share the same "kind" (all packages, all files, all blueprints)?
- Are there stray files among directories or vice versa?
- Do loose top-level files belong in a sub-package?

### 2. Naming Conventions

**Rule**: Names at the same level must follow one consistent convention.

| Convention | Example |
|-----------|---------|
| snake_case | `tool_config_manager.py` |
| kebab-case | `cdmcp-web-exploration/` |
| UPPER_CASE | `GOOGLE.GDS/` (tool names) |

Check:
- Are naming styles mixed at the same level? (e.g., `camelCase` and `snake_case` together)
- Are names excessively long? Consider splitting into subdirectories or shortening.
- Is naming entropy high? (many different patterns = confusion)

### 3. Data vs Code Separation

**Rule**: Code directories must not contain runtime artifacts.

| Item | Correct Location | Wrong Location |
|------|-----------------|----------------|
| JSON config templates | `logic/config/` | OK if they're static defaults |
| Runtime-generated JSON | `data/` or `data/_/runtime/` | `logic/config/` |
| Log files | `data/log/` | `logic/` or any code dir |
| Temporary scripts | `tmp/` or `data/tmp/` | Root of code packages |
| Cache files | `data/cache/` or tool-local `data/` | Code directories |

Check:
- Are there `tmp/`, `log/`, `audit/`, `cache/` folders inside core code directories?
- Are there `.json` data files mixed with `.py` code files?

### 4. Documentation Coverage

**Rule**: Every symmetric root directory must have documentation.

Required at minimum:
- **`README.md`**: Brief overview (1-3 paragraphs) explaining the directory's purpose and organization.
- **`AGENT.md`** (optional): Detailed technical reference for AI agents.

Check:
- Does the directory have a README.md?
- Does the README explain the organizational principle (what goes here, what doesn't)?
- Are sub-packages documented? (At minimum, the first level under each root directory.)

### 5. Extensibility Patterns

**Rule**: Features with expansion potential must use sub-levels, not flags.

- **Bad**: `SKILLS market browse --source clawhub` (new sources need flag values, shared logic)
- **Good**: `SKILLS market clawhub browse` (new sources get their own sub-command namespace)

This applies to:
- CLI sub-commands where multiple implementations exist or are anticipated
- Directory structures where categories will grow (use `type/instance/` not flat)
- Configuration keys where sections will multiply

### 6. Symmetric Root Compliance

**Rule**: Symmetric root directories follow the same structure at every level.

Symmetric roots in AITerminalTools:
- `logic/` — Implementation code
- `data/` — Transient runtime data (gitignored)
- `data/_/runtime/` — Tracked runtime data (git-tracked)
- `interface/` — Public API
- `hooks/` — Event callbacks
- `test/` — Unit tests
- `skills/` — AI agent skills

Check:
- Does each tool have the expected symmetric directories?
- Are there non-standard directories at the tool level?
- Is the project root itself following the same pattern?

## Severity Guide

| Finding | Severity |
|---------|----------|
| Missing README in root directory | warning |
| Data files in code directories | warning |
| Mixed naming conventions | info |
| Structural irregularity (mixed kinds at same level) | warning |
| No documentation for new architecture | critical |
| Extensibility violation (flags instead of sub-commands) | warning |

### 7. Fix Issues Immediately

**Rule**: When you discover bugs, duplicate implementations, stale code, or logic gaps during the audit, fix them immediately rather than deferring.

- Duplicate implementations -> Consolidate into one location, update all callers
- Dead code -> Remove it
- Logic gaps -> Implement the missing piece or document it as a known gap
- Stale references -> Update paths, imports, and documentation

### 8. Seek Feedback on Uncertainty

**Rule**: When constructing README.md or AGENT.md and you encounter ambiguity or design questions, use USERINPUT immediately to get the user's input.

- If the user has no preference, make a reasonable decision and document your reasoning
- If the user provides guidance, incorporate it and continue
- Never guess silently about architectural intent — ask first

### 9. Rename Mismatched Directories

**Rule**: When a directory's name doesn't match the functionality revealed by audit, rename it and refactor all references.

- Directory names must accurately reflect their contents' purpose
- Use temporary batch-replacement scripts for large-scale import path updates
- Create backward-compatibility shims at the old path if needed, but prefer a clean cut

## Workflow

```bash
# 1. Scan a directory
find <dir> -maxdepth 2 -not -path "*/__pycache__/*" | sort

# 2. Check naming consistency
ls <dir>/ | sort    # Visually scan for pattern breaks

# 3. Check for README coverage
for d in <dir>/*/; do
    test -f "${d}README.md" && echo "$(basename $d): OK" || echo "$(basename $d): MISSING"
done

# 4. Record findings as lessons
SKILLS learn "<finding>" --severity warning --tool <tool> --context "<details>"
```

## See Also

- `openclaw` — Self-improvement loop for recording and acting on findings
- `tool-development-workflow` — Standard tool structure requirements
- `code-quality-review` — Static analysis and quality auditing
