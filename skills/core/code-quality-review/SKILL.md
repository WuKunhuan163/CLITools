---
name: code-quality-review
description: Static analysis and quality auditing for AITerminalTools. Covers import rules (IMP001-IMP004), hooks/interface validation, language coverage, and test structure audits.
---

# Code Quality Review

## Import Rules

The `TOOL audit imports` command checks four rules:

| Rule | Description |
|------|-------------|
| IMP001 | Cross-tool imports MUST use `interface/main.py`, never `logic/` directly |
| IMP002 | No circular imports between tools |
| IMP003 | All interface exports must resolve to real modules |
| IMP004 | No wildcard imports (`from x import *`) in interface files |

### Checking Imports

```bash
TOOL audit imports                 # Check all tools
TOOL audit imports --tool GOOGLE   # Check specific tool
TOOL audit imports --fix           # Auto-fix where possible
```

## Hooks & Interface Validation

Every tool exposing cross-tool functionality must have:
- `interface/main.py` with explicit re-exports
- Documented public API in module docstring

```bash
TOOL --dev sanity-check <NAME>           # Validates tool structure
TOOL --dev sanity-check <NAME> --fix     # Auto-creates missing files
```

## Language Coverage Audit

```bash
TOOL lang audit                    # Check translation coverage for all tools
TOOL lang audit --tool <NAME>      # Single tool
TOOL lang audit --turing           # With Turing Machine display
```

Translation rules:
- Every user-facing string must use `_("key", "Default text")`
- No `en.json` file -- English is the code default
- Missing translations fall back to English gracefully

## Test Structure Audit

```bash
TOOL --dev audit-test <NAME>           # Check test file naming
TOOL --dev audit-test <NAME> --fix     # Auto-rename files
```

Rules:
- Files must match `test_XX_name.py` pattern (two-digit index)
- `test_00_help.py` is mandatory
- See `unit-test-conventions` for full details
