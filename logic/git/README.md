# logic/git

Git operations, .gitignore management, and persistence across branch switches.

## Contents

- **engine.py** - Low-level git commands: `run_git_command`, `get_remote_url`, `push_resource_to_remote`, `list_remote_files`, `get_current_branch`, `auto_squash_if_needed`, `auto_push_if_needed`, `push_with_progress`
- **manager.py** - `GitIgnoreManager` (project-wide .gitignore from tool.json), `initialize_git_state`; high-level `sync_dev_logic`, `align_branches_logic`
- **persistence.py** - `GitPersistenceManager` for saving/restoring untracked dirs across branch switches; `get_persistence_manager`
- **utils.py** - Re-exports (minimal)

## Structure

```
git/
  __init__.py
  engine.py
  manager.py
  persistence.py
  utils.py
```
