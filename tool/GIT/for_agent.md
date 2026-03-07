# GIT Tool: Guide for AI Agents

## Overview
The `GIT` tool is a managed proxy for the system `git` command. It is designed to provide human-friendly progress indicators during long-running operations like `push` or `pull`.

## Core Logic
- **`logic/engine.py`**: Contains the `GitEngine` class. Use this for programmatic Git operations within other tools.
- **Progress Implementation**: It uses `logic.utils.run_with_progress` to capture `git`'s own `--progress` output and translate it into a single-line terminal indicator.

## Branch Strategy
This tool enforces the project's linear branch strategy:
1. `dev`: Active development.
2. `tool`: Testing and deployment validation.
3. `main`: Stable framework.
4. `test`: Unit test execution.

## History Maintenance
Agents MUST maintain repository health by following these rules:
1. **Automated Maintenance**: `GIT maintain` should be triggered periodically (every 50 commits) to squash older history.
2. **Frequency Constraints**: Any level/frequency model must satisfy `base * level * frequency = integer`.
3. **Robustness**: Maintenance uses a `reset --hard` and `cherry-pick` strategy. Always ensure you have a clean working tree before starting.
4. **USERINPUT Integration**: `USERINPUT` auto-commits MUST include a rolling tag `#0000` to `#9999` captured in `data/git/tag_counter.txt`.

## Operation Rules
- **Direct Git**: In high-load environments, use `/usr/bin/git` to avoid wrapper overhead and potential process limits.
- **Silent Mode**: Internal calls between tools should use the `run_git_tool_managed` interface from `tool.GIT.interface.main` to avoid output clutter.
- **Bold Phrases**: When reporting success, the entire action (e.g. "**Successfully pushed**") should be bolded.

