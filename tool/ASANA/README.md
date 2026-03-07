# ASANA

Asana project management via Chrome DevTools Protocol (CDP).

## Overview

Uses the authenticated Asana web app session in Chrome to perform REST API operations without a separate Personal Access Token. All calls go through the same-origin API at `app.asana.com/api/1.0/`.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222 --remote-allow-origins=*`
- An active Asana tab (`app.asana.com`) with authenticated session

## Commands

| Command | Description |
|---------|-------------|
| `ASANA me` | Show authenticated user info |
| `ASANA workspaces` | List workspaces |
| `ASANA projects <workspace_gid>` | List projects in a workspace |
| `ASANA tasks <workspace_gid>` | List tasks assigned to me |
| `ASANA create-task <ws_gid> <name>` | Create a new task |
| `ASANA create-project <ws_gid> <name>` | Create a new project |
| `ASANA search <ws_gid> <query>` | Search tasks by text |
| `ASANA complete <task_gid>` | Mark a task as completed |

## Interface

```python
from tool.ASANA.logic.interface.main import (
    find_asana_tab,
    get_me,
    list_workspaces,
    create_task,
)
```
