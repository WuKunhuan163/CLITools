# BOARDMIX — Agent Quick Reference

## Built-in Commands

| Command | Description |
|---------|-------------|
| `BOARDMIX --demo` | Run demo countdown |
| `BOARDMIX --setup` | Run tool setup |
| `BOARDMIX --test` | Run unit tests |
| `BOARDMIX --dev <cmd>` | Developer commands |
| `BOARDMIX --rule` | Show AI rules |
| `BOARDMIX hooks list` | List available hooks |
| `BOARDMIX skills list` | List tool skills |

## MCP Commands Convention

If this tool implements CDMCP browser automation, all MCP commands must use the `--mcp-` prefix.
For example: `BOARDMIX --mcp-boot`, `BOARDMIX --mcp-status`, `BOARDMIX --mcp-navigate <target>`.
The base class transparently rewrites `--mcp-<cmd>` to bare subcommands for argparse compatibility.

## Hooks

This tool supports the hooks system. See `BOARDMIX hooks list` for available events and instances.

## Interface

Other tools can import this tool's interface:
```python
from interface import get_interface
iface = get_interface("BOARDMIX")
info = iface.get_info()
```
