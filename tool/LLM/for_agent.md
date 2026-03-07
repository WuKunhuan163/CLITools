# LLM — Agent Quick Reference

## Built-in Commands

| Command | Description |
|---------|-------------|
| `LLM --demo` | Run demo countdown |
| `LLM --setup` | Run tool setup |
| `LLM --test` | Run unit tests |
| `LLM --dev <cmd>` | Developer commands |
| `LLM --rule` | Show AI rules |
| `LLM hooks list` | List available hooks |
| `LLM skills list` | List tool skills |

## MCP Commands Convention

If this tool implements CDMCP browser automation, all MCP commands must use the `--mcp-` prefix.
For example: `LLM --mcp-boot`, `LLM --mcp-status`, `LLM --mcp-navigate <target>`.
The base class transparently rewrites `--mcp-<cmd>` to bare subcommands for argparse compatibility.

## Hooks

This tool supports the hooks system. See `LLM hooks list` for available events and instances.

## Interface

Other tools can import this tool's interface:
```python
from interface import get_interface
iface = get_interface("LLM")
info = iface.get_info()
```
