# ASANA

Asana project management via Chrome DevTools Protocol (CDP).

## Overview

Uses the authenticated Asana web app session in Chrome to perform REST API operations without a separate Personal Access Token.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222 --remote-allow-origins=*`
- An active Asana tab (`app.asana.com`) with authenticated session

## MCP Commands

All MCP commands use the `--mcp-` prefix.

| Command | Description |
|---------|-------------|
| `--mcp-me` | Show authenticated user info |
| `--mcp-workspaces` | List workspaces |
| `--mcp-projects <workspace_gid>` | List projects in a workspace |
| `--mcp-tasks <workspace_gid>` | List tasks assigned to me |
| `--mcp-create-task <ws_gid> <name>` | Create a new task |
| `--mcp-create-project <ws_gid> <name>` | Create a new project |
| `--mcp-search <ws_gid> <query>` | Search tasks by text |
| `--mcp-complete <task_gid>` | Mark a task as completed |

### Usage

```bash
ASANA --mcp-me
ASANA --mcp-workspaces
ASANA --mcp-tasks <workspace_gid>
ASANA --mcp-create-task <ws_gid> "My Task"
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |
