---
name: error-recovery-patterns
description: Systematic error recovery strategies for multi-step workflows. Covers retry patterns, fallback strategies, partial failure handling, and session recovery.
---

# Error Recovery Patterns

## When to Use

Apply these patterns whenever executing multi-step or network-dependent operations.

## Pattern 1: Retry with Backoff

**Infrastructure**: Use the built-in `retry` decorator:

```python
from interface.utils import retry

@retry(max_attempts=3, backoff=1.0, retryable_exceptions=(ConnectionError, TimeoutError))
def call_api():
    return requests.get(url)
```

The decorator also handles HTTP status code retries (500, 502, 503, 504 by default).

When to use: API calls, network requests, CDP operations.
When NOT to use: Auth failures (retrying won't help), invalid input.

## Pattern 2: Pre-flight Check

Verify conditions before starting expensive operations:

```python
def preflight_check():
    checks = [
        ("Chrome CDP available", is_chrome_cdp_available),
        ("Target tab found", lambda: find_tab(URL) is not None),
        ("Authenticated", lambda: get_auth_state().get("authenticated")),
    ]
    for name, check in checks:
        if not check():
            return False, f"Pre-flight failed: {name}"
    return True, "All checks passed"
```

## Pattern 3: Bulk Operation with Skip-on-Error

For operations on many items where individual failures shouldn't stop the whole batch:

```python
results = {"success": 0, "failed": 0, "skipped": 0, "errors": []}

for item in items:
    try:
        process(item)
        results["success"] += 1
    except RateLimitError:
        time.sleep(5)
        try:
            process(item)
            results["success"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{item}: {e}")
    except Exception as e:
        results["failed"] += 1
        results["errors"].append(f"{item}: {e}")

print(f"Done: {results['success']} ok, {results['failed']} failed")
```

## Pattern 4: Session Recovery

For CDMCP tools where the browser tab can close or become unresponsive:

```
1. Try operation
2. If "tab not found" or "connection refused":
   a. Check if Chrome is still running (CDP port reachable)
   b. If not: prompt user to restart Chrome
   c. If yes: re-find or re-open the tab
   d. Re-inject overlays if needed
   e. Retry operation
3. If still failing after recovery: report and stop
```

## Pattern 5: Checkpoint/Resume

For long-running operations that might be interrupted:

```python
import json
from pathlib import Path

CHECKPOINT_FILE = Path("data/checkpoint.json")

def save_checkpoint(state):
    CHECKPOINT_FILE.write_text(json.dumps(state))

def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text())
    return None

def process_with_checkpoint(items):
    checkpoint = load_checkpoint()
    start_idx = checkpoint.get("last_completed", -1) + 1 if checkpoint else 0
    
    for i, item in enumerate(items[start_idx:], start=start_idx):
        process(item)
        save_checkpoint({"last_completed": i})
    
    CHECKPOINT_FILE.unlink(missing_ok=True)
```

## Pattern 6: Graceful Degradation

When the ideal approach fails, fall back to a simpler method:

```
1. Try: API-based approach (fast, reliable)
2. Fallback: DOM-based approach (slower, more fragile)
3. Last resort: Screenshot + prompt user for help
```

## Decision Matrix

| Error Type | Pattern | Example |
|-----------|---------|---------|
| Network timeout | Retry with backoff | API calls |
| Rate limit (429) | Retry with longer backoff (5-30s) | Bulk messaging |
| Auth expired | Re-authenticate, then retry | Session cookies |
| Element not found | Wait + retry, then DOM scan | CDP click |
| Tab closed | Session recovery | CDMCP operations |
| Partial batch failure | Skip-on-error + report | Bulk operations |
| Long operation interrupted | Checkpoint/resume | Data migration |
| API unavailable | Graceful degradation | Primary -> fallback |

## Common Gotchas

1. **Don't retry auth failures**: If credentials are wrong, retrying wastes time and may trigger lockout.
2. **Log before retrying**: Always record the error before sleeping — silent retries are hard to debug.
3. **Set maximum total time**: Even with retries, cap the total operation time to avoid infinite loops.
4. **Report partial results**: If 90/100 items succeeded, report that — don't hide behind a generic error.

## Related Skills

- `preflight-checks` — validate conditions BEFORE operations to prevent errors
- `task-orchestration` — error handling strategy as part of multi-tool workflows
