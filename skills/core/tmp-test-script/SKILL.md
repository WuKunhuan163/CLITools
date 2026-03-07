---
name: tmp-test-script
description: Conventions for temporary test and one-off scripts in AITerminalTools. Use tmp/ for development verification, not the test suite.
---

# Temporary Test Scripts

## Purpose

The `tmp/` directory is for one-off scripts written during development to verify behavior, test APIs, or debug issues. These are NOT part of the test suite.

## Location

```
tool/<NAME>/tmp/
    test_api_response.py      # Quick API verification
    debug_session_state.py    # Debug a specific issue
    explore_dom.py            # Explore a web page structure
```

## Conventions

1. **Always create in `tmp/`** -- never pollute `test/` with exploratory scripts
2. **Self-contained** -- each script should run independently without test framework
3. **Disposable** -- delete after the issue is resolved
4. **Documented** -- add a docstring explaining what the script verifies

## Template

```python
#!/usr/bin/env python3
"""Verify that [specific behavior] works correctly.

Context: [what prompted this investigation]
Expected: [what should happen]
"""
import sys
from pathlib import Path

# Bootstrap project imports
_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

def main():
    # Test logic here
    result = do_something()
    print(f"Result: {result}")
    assert result == expected, f"Got {result}, expected {expected}"
    print("PASS")

if __name__ == "__main__":
    main()
```

## When to Use

- Investigating an API response format
- Testing a CDP command in isolation
- Verifying a fix before committing
- Exploring an unfamiliar library

## When NOT to Use

- Regression tests (use `test/` with proper naming)
- Performance benchmarks (use dedicated tooling)
- Anything that should persist across sessions

## Cleanup

After resolving the issue, either:
1. Delete the tmp script
2. Promote it to a proper test in `test/` if it covers a regression
