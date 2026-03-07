---
name: preflight-checks
description: Pre-flight check patterns for validating conditions before executing risky or complex operations. Teaches agents to verify prerequisites, confirm bulk operations, and assess risk before proceeding.
---

# Pre-flight Checks

## When to Use

Run pre-flight checks before:
- Bulk operations (messaging many contacts, batch file processing)
- Destructive operations (delete, overwrite, uninstall)
- Operations requiring external services (Chrome CDP, API calls)
- Operations that can't be easily undone

## Infrastructure

The core `preflight()` function and common checks are available as reusable infrastructure:

```python
from logic.utils.preflight import preflight, check_command_exists, check_path_exists, check_port_available

ok, failures = preflight([
    ("Chrome available", lambda: check_command_exists("google-chrome")),
    ("Output dir exists", lambda: check_path_exists("/tmp/output")),
    ("Port 9222 free", lambda: check_port_available(9222)),
])
```

Also importable from `logic.utils`:

```python
from logic.utils import preflight, check_command_exists, check_path_exists, check_port_available
```

## Standard Check Categories

### 1. Connectivity Checks (CDMCP tools)

```python
checks = [
    ("Chrome CDP available", lambda: is_chrome_cdp_available()),
    ("Target tab found", lambda: find_tab(URL) is not None),
    ("Session authenticated", lambda: get_auth_state().get("authenticated")),
]
ok, failures = preflight(checks)
if not ok:
    print(f"Pre-flight failed: {', '.join(failures)}")
    return
```

### 2. Resource Checks (file/data tools)

```python
checks = [
    ("Input file exists", lambda: Path(input_path).exists()),
    ("Output dir writable", lambda: os.access(output_dir, os.W_OK)),
    ("Sufficient disk space", lambda: shutil.disk_usage("/").free > MIN_SPACE),
]
```

### 3. Configuration Checks (API tools)

```python
checks = [
    ("API key configured", lambda: os.environ.get("API_KEY")),
    ("Config file exists", lambda: config_path.exists()),
    ("Required dependencies installed", lambda: check_dependencies()),
]
```

## Guard Rails for Risky Operations

### Bulk Operation Confirmation

Before executing bulk operations (>10 items), always:
1. Display the count and nature of the operation
2. Show a sample of what will be affected
3. Ask for confirmation if the operation is destructive

```python
if len(targets) > 10:
    print(f"About to process {len(targets)} items.")
    print(f"Sample: {', '.join(str(t) for t in targets[:3])}...")
    # In interactive mode, confirm via USERINPUT
    # In automated mode, proceed with caution logging
```

### Rate Limit Guard

For tools that interact with rate-limited services:

```python
import time
import random

MIN_DELAY = 2.0  # seconds
MAX_DELAY = 5.0  # seconds
CONSECUTIVE_FAIL_LIMIT = 3

consecutive_fails = 0
for item in items:
    try:
        result = process(item)
        consecutive_fails = 0
    except RateLimitError:
        consecutive_fails += 1
        if consecutive_fails >= CONSECUTIVE_FAIL_LIMIT:
            print(f"Stopped: {CONSECUTIVE_FAIL_LIMIT} consecutive rate limit errors")
            break
        time.sleep(MIN_DELAY * (2 ** consecutive_fails))
        continue
    
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
```

### Destructive Operation Guard

Before destructive operations:

```python
DESTRUCTIVE_KEYWORDS = ["delete", "remove", "uninstall", "drop", "purge", "force"]

def is_destructive(command):
    return any(kw in command.lower() for kw in DESTRUCTIVE_KEYWORDS)

if is_destructive(operation):
    print(f"WARNING: This operation is destructive: {operation}")
    # Require explicit confirmation
```

## Risk Assessment Matrix

| Operation | Risk Level | Required Check |
|-----------|-----------|----------------|
| Read data | Low | Connectivity only |
| Send 1 message | Low | Auth + connectivity |
| Send >10 messages | Medium | Auth + connectivity + rate limit + confirmation |
| Delete files | High | Existence + confirmation + backup suggestion |
| Modify config | Medium | Backup existing + validation |
| Install packages | Medium | Dependency check + compatibility |
| Bulk operations | High | All checks + confirmation + progress tracking |

## Integration with Error Recovery

Pre-flight checks work together with the `error-recovery-patterns` skill:
1. **Pre-flight**: Catch problems before they happen
2. **Error recovery**: Handle problems that slip through pre-flight
3. **Introspection**: Learn from failures to improve pre-flight checks over time

Use `SKILLS introspect` to identify which tools have the most errors, then add targeted pre-flight checks.
