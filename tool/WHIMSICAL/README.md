# WHIMSICAL

WHIMSICAL tool template.

## Quick Start

```bash
WHIMSICAL --demo         # Run demo
WHIMSICAL --setup        # Install dependencies
WHIMSICAL --help         # Show help
```

## MCP Commands

If this tool implements CDMCP browser automation, all MCP commands use the `--mcp-` prefix:

```bash
WHIMSICAL --mcp-boot          # Boot session
WHIMSICAL --mcp-status        # Check status
WHIMSICAL --mcp-<command>     # Any MCP operation
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
WHIMSICAL hooks list                  # List events and instances
WHIMSICAL hooks enable demo_logger    # Enable the demo logger hook
WHIMSICAL hooks disable demo_logger   # Disable it
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
iface = get_interface("WHIMSICAL")
info = iface.get_info()  # {"name": "WHIMSICAL", "version": "1.0.0"}
```

## Testing

```bash
TOOL --test WHIMSICAL
```
