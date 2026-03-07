# COGGLE

COGGLE tool template.

## Quick Start

```bash
COGGLE --demo         # Run demo
COGGLE --setup        # Install dependencies
COGGLE --help         # Show help
```

## MCP Commands

If this tool implements CDMCP browser automation, all MCP commands use the `--mcp-` prefix:

```bash
COGGLE --mcp-boot          # Boot session
COGGLE --mcp-status        # Check status
COGGLE --mcp-<command>     # Any MCP operation
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
COGGLE hooks list                  # List events and instances
COGGLE hooks enable demo_logger    # Enable the demo logger hook
COGGLE hooks disable demo_logger   # Disable it
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
iface = get_interface("COGGLE")
info = iface.get_info()  # {"name": "COGGLE", "version": "1.0.0"}
```

## Testing

```bash
TOOL --test COGGLE
```
