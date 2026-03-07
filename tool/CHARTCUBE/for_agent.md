# CHARTCUBE — Agent Quick Reference

## Built-in Commands

| Command | Description |
|---------|-------------|
| `CHARTCUBE --demo` | Run demo countdown |
| `CHARTCUBE --setup` | Run tool setup |
| `CHARTCUBE --test` | Run unit tests |
| `CHARTCUBE --dev <cmd>` | Developer commands |
| `CHARTCUBE --rule` | Show AI rules |
| `CHARTCUBE hooks list` | List available hooks |
| `CHARTCUBE skills list` | List tool skills |

## MCP Commands Convention

If this tool implements CDMCP browser automation, all MCP commands must use the `--mcp-` prefix.
For example: `CHARTCUBE --mcp-boot`, `CHARTCUBE --mcp-status`, `CHARTCUBE --mcp-navigate <target>`.
The base class transparently rewrites `--mcp-<cmd>` to bare subcommands for argparse compatibility.

## Hooks

This tool supports the hooks system. See `CHARTCUBE hooks list` for available events and instances.

## Interface

Other tools can import this tool's interface:
```python
from interface import get_interface
iface = get_interface("CHARTCUBE")
info = iface.get_info()
```
