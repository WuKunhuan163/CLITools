---
name: exploratory-testing
description: Systematic exploration of unknown behaviors using tmp/ test scripts. Use when investigating APIs, protocols, or integrations where the correct approach is not yet known.
---

# Exploratory Testing

## When to Use

Use exploratory testing when:
- Integrating with an unfamiliar API or protocol
- The documentation is incomplete or unclear
- You need to discover the correct parameters experimentally
- Debugging an issue where the root cause is unknown

## Process

### 1. Create a Focused Script

```bash
mkdir -p tool/<NAME>/tmp
```

Write a minimal script that isolates the question:

```python
#!/usr/bin/env python3
"""Explore: What format does the API return for paginated results?"""
# Bootstrap...
import requests
resp = requests.get("https://api.example.com/items?page=1")
print(f"Status: {resp.status_code}")
print(f"Headers: {dict(resp.headers)}")
print(f"Body keys: {list(resp.json().keys())}")
```

### 2. Iterate with Logging

Write findings to a debug log:

```python
import json
from pathlib import Path

LOG = Path(__file__).parent / "explore_api.log"

def log(msg, data=None):
    with open(LOG, "a") as f:
        f.write(json.dumps({"msg": msg, "data": data}) + "\n")
```

### 3. Document Findings

When you discover the correct approach, document it:
- Update the tool's `README.md` or `for_agent.md`
- If the finding is a reusable pattern, create or update a skill
- If it reveals a bug, capture a lesson via `SKILLS learn`

### 4. Clean Up

Delete the tmp scripts and logs once the knowledge is captured elsewhere.

## Guidelines

1. Keep each script focused on ONE question
2. Log everything -- you'll need it when the behavior changes
3. Use descriptive filenames: `tmp/explore_oauth_flow.py`, not `tmp/test.py`
4. Never leave tmp scripts as the only documentation of a finding

## Related Skills

- `tmp-test-script` — conventions for the tmp/ directory (naming, cleanup, template)
- `development-iteration-protocol` — escalating test requirements on repeated failures
