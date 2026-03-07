# TODO — Agent Quick Reference

## Built-in Commands

| Command | Description |
|---------|-------------|
| `TODO --demo` | Run demo countdown |
| `TODO --setup` | Run tool setup |
| `TODO --test` | Run unit tests |
| `TODO --dev <cmd>` | Developer commands |
| `TODO --rule` | Show AI rules |
| `TODO hooks list` | List available hooks |
| `TODO skills list` | List tool skills |

## MCP Commands Convention

If this tool implements CDMCP browser automation, all MCP commands must use the `--mcp-` prefix.
For example: `TODO --mcp-boot`, `TODO --mcp-status`, `TODO --mcp-navigate <target>`.
The base class transparently rewrites `--mcp-<cmd>` to bare subcommands for argparse compatibility.

## Hooks

This tool supports the hooks system. See `TODO hooks list` for available events and instances.

## Interface

Other tools can import this tool's interface:
```python
from interface import get_interface
iface = get_interface("TODO")
info = iface.get_info()
```
