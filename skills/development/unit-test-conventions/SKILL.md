---
name: unit-test-conventions
description: Naming conventions, structure, and best practices for unit tests in AITerminalTools. Use when creating new tests, auditing test files, or adding test suites to tools.
---

# Unit Test Conventions

## File Naming

All unit test files MUST follow the pattern:

```
test_XX_descriptive_name.py
```

- `XX` is a **two-digit sequential number** starting from `00`.
- `test_00_help.py` is **mandatory** for every tool (validates `--help` flag).
- Numbers indicate execution order and logical grouping.

### Numbering Guidelines

| Range | Purpose |
|-------|---------|
| `00-09` | Core setup: help, basic CLI, structure checks |
| `10-19` | Feature-specific unit tests |
| `20-29` | Integration tests (cross-module) |
| `30-49` | Advanced / workflow tests |
| `100+` | Complex / long-running suites |

### Examples

```
test_00_help.py             # Mandatory: validates --help
test_01_overlay_visual.py   # Feature: overlay rendering
test_02_full_workflow.py    # Feature: end-to-end workflow
test_03_session_boot.py     # Feature: session lifecycle
test_04_session_reboot.py   # Feature: session recovery
test_10_remount.py          # Integration: remount flow
test_20_remote_echo.py      # Integration: remote commands
test_100_gds_complex.py     # Complex: full GDS suite
```

## File Structure

Every test file should define these constants at the top:

```python
EXPECTED_TIMEOUT = 300       # Max seconds before test is killed
EXPECTED_CPU_LIMIT = 40.0    # Max CPU % threshold
SEQUENTIAL = True            # (Optional) Run this test alone, after parallel tests
```

### Sequential Execution

Add `SEQUENTIAL = True` at the top of a test file to mark it for isolated, sequential execution. Sequential tests run **after** all parallel tests have finished, one at a time in numeric order.

Use this when:
- Tests modify shared state (files, config, environment)
- Tests depend on each other's side effects
- Tests require exclusive system resources

## Execution

```bash
TOOL --test <TOOL_NAME>           # Run all tests for a tool
TOOL --test <TOOL_NAME> -k 03    # Run specific test by number
```

## Auditing

```bash
TOOL --dev audit-test <NAME>       # Check naming convention
TOOL --dev audit-test <NAME> --fix # Auto-fix naming issues
TOOL_NAME --dev audit-test         # Per-tool audit
```

## Common Mistakes

1. **No number prefix**: `test_session_boot.py` -- must be `test_03_session_boot.py`
2. **Single-digit number**: `test_3_boot.py` -- must be `test_03_boot.py`
3. **Missing test_00_help.py**: Every tool requires this file
4. **Gaps in numbering**: Acceptable but discouraged; keep numbers contiguous within ranges

## Test Maturation: From Features to Tests

As tools mature through real-world usage, their features and behaviors MUST be stabilized into unit tests. This ensures:
- Functionality remains stable across refactoring and migrations.
- Regressions are caught immediately, with the failing test pointing to the broken feature.
- New agents can understand what a tool does by reading its test suite.

### When to Write Tests

Follow this progression:
1. **Initial development**: `test_00_help.py` only (mandatory).
2. **Feature stabilization**: After a feature works reliably in practice, write a test for it. Each distinct feature, CLI option, or integration point gets its own test file.
3. **Bug fix**: Every non-trivial bug fix should include a regression test.
4. **Migration**: After migrating code (e.g., imports, paths, backends), run all existing tests to verify nothing broke.

### What NOT to Test

- Highly interactive tools (e.g., OPENCLAW's live agent loop) are exempt from comprehensive unit testing. Focus on testable components (CLI parsing, config loading, message formatting).
- Network-dependent operations should use mocking or skip gracefully when offline.

### Localization in Tests

Tests must not hardcode English strings from the UI. Use regex to strip ANSI codes and accept either English or localized strings:

```python
import re
plain = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
self.assertTrue("Expected" in plain or "预期" in plain)
```

## Temporary Test Scripts

For one-off verification during development, use `tmp/` directory instead of the test suite. Run `SKILLS show tmp-test-script` for patterns.
