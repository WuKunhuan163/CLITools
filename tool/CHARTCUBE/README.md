# CHARTCUBE

CHARTCUBE tool template.

## Quick Start

```bash
CHARTCUBE --demo         # Run demo
CHARTCUBE --setup        # Install dependencies
CHARTCUBE --help         # Show help
```

## MCP Commands

If this tool implements CDMCP browser automation, all MCP commands use the `--mcp-` prefix:

```bash
CHARTCUBE --mcp-boot          # Boot session
CHARTCUBE --mcp-status        # Check status
CHARTCUBE --mcp-<command>     # Any MCP operation
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
CHARTCUBE hooks list                  # List events and instances
CHARTCUBE hooks enable demo_logger    # Enable the demo logger hook
CHARTCUBE hooks disable demo_logger   # Disable it
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
iface = get_interface("CHARTCUBE")
info = iface.get_info()  # {"name": "CHARTCUBE", "version": "1.0.0"}
```

## Testing

```bash
TOOL --test CHARTCUBE
```
