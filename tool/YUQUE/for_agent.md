# YUQUE — Agent Quick Reference

## Built-in Commands

| Command | Description |
|---------|-------------|
| `YUQUE --demo` | Run demo countdown |
| `YUQUE --setup` | Run tool setup |
| `YUQUE --test` | Run unit tests |
| `YUQUE --dev <cmd>` | Developer commands |
| `YUQUE --rule` | Show AI rules |
| `YUQUE hooks list` | List available hooks |
| `YUQUE skills list` | List tool skills |

## MCP Commands Convention

If this tool implements CDMCP browser automation, all MCP commands must use the `--mcp-` prefix.
For example: `YUQUE --mcp-boot`, `YUQUE --mcp-status`, `YUQUE --mcp-navigate <target>`.
The base class transparently rewrites `--mcp-<cmd>` to bare subcommands for argparse compatibility.

## Hooks

This tool supports the hooks system. See `YUQUE hooks list` for available events and instances.

## Interface

Other tools can import this tool's interface:
```python
from interface import get_interface
iface = get_interface("YUQUE")
info = iface.get_info()
```
