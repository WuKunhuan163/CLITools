# COGGLE — Agent Quick Reference

## Built-in Commands

| Command | Description |
|---------|-------------|
| `COGGLE --demo` | Run demo countdown |
| `COGGLE --setup` | Run tool setup |
| `COGGLE --test` | Run unit tests |
| `COGGLE --dev <cmd>` | Developer commands |
| `COGGLE --rule` | Show AI rules |
| `COGGLE hooks list` | List available hooks |
| `COGGLE skills list` | List tool skills |

## MCP Commands Convention

If this tool implements CDMCP browser automation, all MCP commands must use the `--mcp-` prefix.
For example: `COGGLE --mcp-boot`, `COGGLE --mcp-status`, `COGGLE --mcp-navigate <target>`.
The base class transparently rewrites `--mcp-<cmd>` to bare subcommands for argparse compatibility.

## Hooks

This tool supports the hooks system. See `COGGLE hooks list` for available events and instances.

## Interface

Other tools can import this tool's interface:
```python
from interface import get_interface
iface = get_interface("COGGLE")
info = iface.get_info()
```
