---
name: standard-command-development
description: Interface-oriented design guide covering standard development flows and three-layer architecture for all command types.
---

# Standard Command Development

## Three-Layer Architecture

Every command follows a three-layer pattern:

```
Command Entry (main.py)     -> Parses CLI args, calls logic
Logic API (logic/*.py)      -> Business logic, no I/O formatting
Interface (interface/main.py) -> Public API for cross-tool use
```

### Layer 1: Command Entry

```python
# tool/<NAME>/main.py
class MyTool(ToolBase):
    def run(self, args):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        sub.add_parser("status", help="Show status")
        args = parser.parse_args(args)
        
        if args.command == "status":
            result = my_logic.get_status()  # Call Layer 2
            print(f"  Status: {result['state']}")
```

### Layer 2: Logic API

```python
# tool/<NAME>/logic/core.py
def get_status() -> dict:
    """Pure logic, returns structured data. No print statements."""
    return {"state": "running", "uptime": 3600}
```

### Layer 3: Interface

```python
# tool/<NAME>/interface/main.py
from tool.<NAME>.logic.core import get_status  # noqa: F401
```

## Standard Command Prefixes

All commands use `--` prefix for consistency:

```bash
TOOL_NAME --config          # Configuration
TOOL_NAME --install         # Installation
TOOL_NAME --dev <cmd>       # Developer commands
TOOL_NAME --test            # Run tests
TOOL_NAME --mcp-<cmd>       # MCP operations (CDMCP tools)
```

## Guidelines

1. Logic layer returns data structures, never prints
2. Command layer handles ALL user-facing output
3. Interface layer re-exports, never adds logic
4. Use type hints on logic layer functions
5. Keep logic testable in isolation (no CLI dependencies)
