# MIRO

MIRO tool template.

## Quick Start

```bash
MIRO --demo         # Run demo
MIRO --setup        # Install dependencies
MIRO --help         # Show help
```

## MCP Commands

If this tool implements CDMCP browser automation, all MCP commands use the `--mcp-` prefix:

```bash
MIRO --mcp-boot          # Boot session
MIRO --mcp-status        # Check status
MIRO --mcp-<command>     # Any MCP operation
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |

## Hooks

Event-driven callback system.

```bash
MIRO hooks list                  # List events and instances
MIRO hooks enable demo_logger    # Enable the demo logger hook
MIRO hooks disable demo_logger   # Disable it
```

### Hook Events

| Event | Description |
|-------|-------------|
| `on_tool_start` | Fired when the tool begins execution (base) |
| `on_tool_exit` | Fired when the tool finishes execution (base) |
| `on_demo_action` | Fired during --demo countdown |

## Interface

```python
from interface import get_interface
iface = get_interface("MIRO")
info = iface.get_info()  # {"name": "MIRO", "version": "1.0.0"}
```

## Testing

```bash
TOOL --test MIRO
```
