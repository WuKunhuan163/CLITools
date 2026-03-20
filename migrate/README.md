# migrate/

Migration domains for importing tools, infrastructure, and resources from external sources.

## Usage

```bash
TOOL --migrate --help                    # Show all domains and levels
TOOL --migrate --<level> <domain> [opts] # Execute migration
```

## Levels

| Level | Description |
|-------|-------------|
| `--tool` | Complete, ready-to-use tool |
| `--infrastructure` | Code resources used by a tool (e.g. Python builds) |
| `--hooks` | Lifecycle hooks |
| `--mcp` | MCP server definitions |
| `--skills` | Skill definitions |
| `--info` | Metadata/documentation only |
| `--draft-tool` | Tool scaffold needing post-processing |
| `--draft-infrastructure` | Infrastructure needing post-processing |
| `--draft-hooks` | Hooks needing post-processing |
| `--draft-mcp` | MCP definitions needing post-processing |

## Domains

| Domain | Levels | Description |
|--------|--------|-------------|
| CLI-Anything | draft-tool, skills, info | Agent-native CLI harnesses (Blender, GIMP, etc.) |
| astral-sh | infrastructure | Standalone Python builds |

## Structure

```
migrate/
  <domain>/
    info.json           # Domain metadata + supported levels
    __init__.py
    <level>.py          # Migration implementation (e.g. draft_tool.py)
    check.py            # Optional: check pending migrations
```
