# CLIANYTHING — Agent Quick Reference

## Built-in Commands

| Command | Description |
|---------|-------------|
| `CLIANYTHING --demo` | Run demo countdown |
| `CLIANYTHING --setup` | Run tool setup |
| `CLIANYTHING --test` | Run unit tests |
| `CLIANYTHING --dev <cmd>` | Developer commands |
| `CLIANYTHING --rule` | Show AI rules |
| `CLIANYTHING hooks list` | List available hooks |
| `CLIANYTHING skills list` | List tool skills |

## MCP Commands Convention

If this tool implements CDMCP browser automation, all MCP commands must use the `--mcp-` prefix.
For example: `CLIANYTHING --mcp-boot`, `CLIANYTHING --mcp-status`, `CLIANYTHING --mcp-navigate <target>`.
The base class transparently rewrites `--mcp-<cmd>` to bare subcommands for argparse compatibility.

## Hooks

This tool supports the hooks system. See `CLIANYTHING hooks list` for available events and instances.

## Interface

Other tools can import this tool's interface:
```python
from interface import get_interface
iface = get_interface("CLIANYTHING")
info = iface.get_info()
```
