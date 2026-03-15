---
name: tmp-test-script
description: Conventions for the symmetric tmp/ directory in AITerminalTools. Covers temporary scripts, data, prototypes, exploratory code, and mandatory cleanup.
---

# Temporary Directory (`tmp/`)

## Purpose

Every tool and the project root has a `tmp/` directory for ephemeral artifacts: test scripts, debug data, prototypes, feasibility explorations, and bug investigations. Nothing in `tmp/` is permanent.

## Location

```
/Applications/AITerminalTools/tmp/          # Root-level tmp
tool/<NAME>/tmp/                            # Per-tool tmp
```

Both follow the same conventions.

## What Goes in `tmp/`

| Type | Examples | Lifecycle |
|------|----------|-----------|
| **Test scripts** | `test_api_response.py`, `verify_fix.py` | Delete after issue resolved |
| **Debug data** | `debug_session.json`, `dump_state.log` | Delete after root-cause found |
| **Prototypes** | `poc_new_hook.py`, `draft_ui.html` | Promote to proper location or delete |
| **Exploration** | `explore_dom.py`, `try_websocket.py` | Delete after approach validated |
| **Transcripts** | `eval-round4-plan.md`, `agent_trace.json` | Delete or move to `data/report/` |

## Conventions

1. **Self-contained** — each file runs independently without test frameworks
2. **Documented** — add a docstring or header comment explaining what and why
3. **Disposable** — treat everything in `tmp/` as deletable at any time
4. **No imports from `tmp/`** — other code must never `import` from tmp files
5. **No secrets** — never store API keys, tokens, or credentials

## Template

```python
#!/usr/bin/env python3
"""Verify that [specific behavior] works correctly.

Context: [what prompted this investigation]
Expected: [what should happen]
"""
import sys
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

def main():
    result = do_something()
    print(f"Result: {result}")
    assert result == expected, f"Got {result}, expected {expected}"
    print("PASS")

if __name__ == "__main__":
    main()
```

## Cleanup Rules

**When purpose is achieved:**
1. Test passed / bug fixed → **delete** the script and data
2. Prototype validated → **promote** code to its proper location (e.g., `logic/`, `test/`), then delete the tmp file
3. Exploration complete → **record** findings in a report (`data/report/` or `for_agent.md`), then delete

**Periodic cleanup:**
- Before starting a new major task, scan `tmp/` for stale files
- Files older than 7 days without active reference should be deleted
- The `TOOL --audit code` system may flag large or stale tmp directories

## When to Use

- Investigating an API response or protocol behavior
- Testing a CDP/MCP command in isolation
- Verifying a fix before committing
- Exploring an unfamiliar library or integration
- Drafting a prototype before building the real implementation
- Recording temporary agent evaluation transcripts

## When NOT to Use

- Regression tests → use `test/` with `test_NN_name.py` naming
- Persistent reports → use `data/report/`
- Reusable utilities → use `logic/`
- Configuration → use `data/config.json`

## Discovery

This skill should be prompted when an agent:
- Creates files directly in the project root instead of `tmp/`
- Leaves exploration artifacts in `logic/` or `test/`
- Asks where to put temporary debug/test scripts
- Has accumulated 5+ files in `tmp/` without cleanup
