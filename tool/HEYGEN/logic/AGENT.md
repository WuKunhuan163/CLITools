# HEYGEN Logic — Technical Reference

## mcp/main.py

Returns `MCPToolConfig` defining:
- `tool_name`: "HEYGEN"
- `mcp_server`: MCP server identifier
- `package_type`: npm or pip
- `capabilities`: List of supported operations
- `required_env`: Environment variables needed for API auth

## Gotchas

1. **Minimal logic layer**: Core functionality is provided by the external MCP server package. This tool's logic only defines the MCP configuration.
2. **Setup required**: Run `HEYGEN setup` before first use to install the MCP server package and configure API keys.
