# WHIMSICAL — Agent Quick Reference

## Built-in Commands

| Command | Description |
|---------|-------------|
| `WHIMSICAL --demo` | Run demo countdown |
| `WHIMSICAL --setup` | Run tool setup |
| `WHIMSICAL --test` | Run unit tests |
| `WHIMSICAL --dev <cmd>` | Developer commands |
| `WHIMSICAL --rule` | Show AI rules |
| `WHIMSICAL hooks list` | List available hooks |
| `WHIMSICAL skills list` | List tool skills |

## MCP Commands Convention

If this tool implements CDMCP browser automation, all MCP commands must use the `--mcp-` prefix.
For example: `WHIMSICAL --mcp-boot`, `WHIMSICAL --mcp-status`, `WHIMSICAL --mcp-navigate <target>`.
The base class transparently rewrites `--mcp-<cmd>` to bare subcommands for argparse compatibility.

## Hooks

This tool supports the hooks system. See `WHIMSICAL hooks list` for available events and instances.

## Interface

Other tools can import this tool's interface:
```python
from interface import get_interface
iface = get_interface("WHIMSICAL")
info = iface.get_info()
```
