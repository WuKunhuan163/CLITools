# logic/_/base/ — Framework Core

## Contents

- `blueprint/base.py` — `ToolBase`: base class for all tools
- `blueprint/mcp.py` — `MCPToolBase`: base class for Chrome CDP-based tools
- `cli.py` — `CliEndpoint`: base class for all `cli.py` command endpoints

## CliEndpoint Pattern

Every `cli.py` in the project inherits from `CliEndpoint`. The endpoint receives a context dict and implements `dispatch(ctx)` or `handle(args)`.

```python
from logic._._ import EcoCommand  # alias for CliEndpoint

class MyCommand(EcoCommand):
    name = "mycommand"
    usage = "TOOL ---mycommand [options]"

    def handle(self, args):
        # args = remaining tokens after eco routing
        self.success("Done.", detail="some detail")
        return 0
```

## ToolBase Routing

`ToolBase.handle_command_line()` performs stateless routing:

1. Strip `-<decorator>` flags from argv
2. Extract `---<eco>` tokens and dispatch via `logic/_/<name>/cli.py`
3. Check subtool delegation (`tool/<NAME>/tool/<CMD>/main.py`)
4. Fall through to the tool's own argparse parser

## __/ Co-Located Data Convention

Endpoint directories may contain a `__/` subdirectory for data tightly coupled to that endpoint:

```
logic/_/audit/
├── cli.py           # The endpoint
├── argparse.json    # Schema
├── __/              # Co-located data
│   ├── templates/   # Report templates
│   └── fixtures/    # Test fixtures for this endpoint
└── code_quality.py  # Implementation modules
```

Rules:
- Only the parent `cli.py` (or sibling modules) may reference `__/` contents
- No business logic in `__/` — only data, fixtures, templates, schemas
- `TOOL ---audit` verifies referential integrity (nothing outside references `__/`)
- This prevents `__/` from becoming a dumping ground
