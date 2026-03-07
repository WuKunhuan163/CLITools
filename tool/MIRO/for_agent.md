# MIRO — Agent Quick Reference

## Built-in Commands

| Command | Description |
|---------|-------------|
| `MIRO --demo` | Run demo countdown |
| `MIRO --setup` | Run tool setup |
| `MIRO --test` | Run unit tests |
| `MIRO --dev <cmd>` | Developer commands |
| `MIRO --rule` | Show AI rules |
| `MIRO hooks list` | List available hooks |
| `MIRO skills list` | List tool skills |

## MCP Commands Convention

If this tool implements CDMCP browser automation, all MCP commands must use the `--mcp-` prefix.
For example: `MIRO --mcp-boot`, `MIRO --mcp-status`, `MIRO --mcp-navigate <target>`.
The base class transparently rewrites `--mcp-<cmd>` to bare subcommands for argparse compatibility.

## Hooks

This tool supports the hooks system. See `MIRO hooks list` for available events and instances.

## Interface

Other tools can import this tool's interface:
```python
from interface import get_interface
iface = get_interface("MIRO")
info = iface.get_info()
```
