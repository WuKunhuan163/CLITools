# logic/git - Agent Reference

## Key Interfaces

### engine.py
- `run_git_command(args, cwd=None, capture_output=True, text=True, silent=False)` - Uses `/usr/bin/git`; returns subprocess result or None
- `get_current_branch(cwd=None)` - Current branch name
- `push_with_progress(remote, branch, cwd, silent_success)` - Push with erasable status line; localized output
- `auto_push_if_needed(remote, branch, interval=3, cwd)` - Push when commit count % interval == 0
- `auto_squash_if_needed(cwd, config)` - Long-tail commit squashing via commit-tree; keeps recent commits intact

### manager.py
- `GitIgnoreManager(project_root)` - **Auto-generates `.gitignore`** from `base_patterns` + tool.json `git_ignore` entries. NEVER edit `.gitignore` directly — add new root directories to `base_patterns` instead.
  - `generate()` - Returns full `.gitignore` content as string
  - `rewrite()` - Writes generated content to `.gitignore` (called by `initialize_git_state` and `sync_dev_logic`)
  - `base_patterns` - Defines which root directories are tracked: `logic/`, `interface/`, `bin/`, `test/`, `tool/`, `report/`, `skills/`, `research/`, `data/_/runtime/`
  - `get_tool_rules()` - Reads `"git_ignore"` from each tool's `tool.json` to generate tool-specific rules
- `initialize_git_state(project_root)` - Calls GitIgnoreManager.rewrite()
- `sync_dev_logic(project_root, quiet, translation_func)` - Auto-commit, push if on dev
- `align_branches_logic(project_root, quiet, translation_func)` - dev -> tool -> main -> test alignment; preserves resource/ on tool branch

### persistence.py
- `GitPersistenceManager(project_root)` - Temp storage at `$TMPDIR/aitools_git_persistence`
- `save(paths)` - Returns locker key; max 8 caches, deletes half when exceeded
- `restore(key)` - Restores and deletes locker
- `save_tools_persistence()` - Saves all `persistence_dirs` from tool.json
- `get_persistence_manager(project_root)` - Factory

## Usage Patterns

1. Before branch switch: `pm.save_tools_persistence()` -> locker_key; after: `pm.restore(locker_key)`
2. `align_branches_logic` uses Turing stages; call from dev sync/align commands
3. GitIgnoreManager base patterns include `**/data/`, `**/resource/`; tool rules append from tool.json `git_ignore`

## Gotchas

- **`.gitignore` is auto-generated**: `GitIgnoreManager.rewrite()` overwrites `.gitignore` on every sync. To track a new root directory, add `"!/your_dir/"` to `base_patterns` in `manager.py`. To add tool-specific ignores, use `"git_ignore"` in `tool.json`.
- `run_git_command` uses `/usr/bin/git` explicitly
- Persistence uses `shutil.copytree`/`copy2`; paths must be under project_root
- `align_main` uses side index to exclude tool/resource/data/tmp/bin from main branch
