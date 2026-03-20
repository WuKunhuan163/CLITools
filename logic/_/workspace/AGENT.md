# logic/workspace/ — Workspace Management

## Overview

A workspace is an external directory mounted into the AITerminalTools system. Unlike Cursor's "Open Folder" which stores config in the target directory, workspace metadata and brain data are stored centrally in `workspace/<hash_id>/`.

## Key Concept

When a user says "open my project at /home/user/my-app", we:
1. Generate a deterministic hash ID from the absolute path
2. Create `workspace/<hash_id>/` with brain, metadata, README, AGENT.md
3. Track the workspace as active in `workspace/.active`

This avoids polluting the user's directory and enables integrated management.

## CLI Commands

```bash
TOOL --create-workspace <path> [--type <blueprint>] [--name <name>]
TOOL --open-workspace <id>
TOOL --close-workspace
TOOL --delete-workspace <id>
TOOL --list-workspaces
TOOL --workspace               # Show active workspace
```

## Filesystem Layout

```
workspace/
├── .active                    # Active workspace ID
└── <hash_id>/
    ├── workspace.json         # Metadata (path, name, created, blueprint, status)
    ├── brain/                 # Brain instance (scoped to this workspace)
    │   ├── working/           # Tasks, context, activity
    │   ├── knowledge/         # Lessons
    │   └── episodic/          # Personality, memory, daily logs
    ├── README.md              # Auto-generated workspace overview
    └── AGENT.md           # Agent guidance for this workspace
```

## Interface

```python
from interface.workspace import get_workspace_manager

wm = get_workspace_manager()
info = wm.create_workspace("/path/to/project")
wm.open_workspace(info["id"])
wm.close_workspace()
```

## Notes

- `workspace/` is gitignored (deny-by-default pattern)
- Brain data in workspaces uses the same blueprint system as `runtime/_/eco/brain/`
- When no workspace is open, the default scope is the AITerminalTools root
- FILEDIALOG integration: if no path is given to `--create-workspace`, the system opens a directory picker
