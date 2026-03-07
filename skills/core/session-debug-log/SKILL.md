---
name: session-debug-log
description: Session logging and debug log system in AITerminalTools. Covers tool.log(), SessionLogger, and log file management.
---

# Session Debug Logging

## Overview

Every tool has access to structured logging via the `tool.log()` method and the `SessionLogger` system.

## Basic Logging

```python
class MyTool(ToolBase):
    def run(self, args):
        self.log("Starting operation...")
        try:
            result = do_work()
            self.log(f"Completed: {result.count} items")
        except Exception as e:
            self.log(f"Error: {e}", level="error")
```

## SessionLogger

For cross-module logging within a single tool session:

```python
from logic.utils.logging import SessionLogger

logger = SessionLogger("MY_TOOL")
logger.info("Session started")
logger.debug("Verbose detail")
logger.error("Something went wrong")
```

## Log File Location

```
tool/<NAME>/data/logs/
    session_YYYY-MM-DD.log     # Daily log file
```

## Debug Technique: Temporary Log Files

When debugging complex issues, create a temporary log in `tmp/`:

```python
import json
from pathlib import Path

debug_log = Path(__file__).resolve().parent / "tmp" / "debug.log"
debug_log.parent.mkdir(exist_ok=True)

def log_debug(msg, data=None):
    with open(debug_log, "a") as f:
        entry = {"msg": msg}
        if data:
            entry["data"] = data
        f.write(json.dumps(entry) + "\n")
```

This approach is preferred over print-debugging because:
- Output doesn't mix with user-facing console messages
- Structured JSON enables grep/jq analysis
- Files persist after the session ends

## Guidelines

1. Use `tool.log()` for standard operational logging
2. Use `SessionLogger` for cross-module tracing within a tool
3. Use `tmp/` debug logs for temporary investigation (clean up after)
4. Never log secrets, tokens, or user credentials
5. Keep log messages actionable: include what happened and what to check
