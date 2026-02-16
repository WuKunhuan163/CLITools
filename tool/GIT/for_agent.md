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

## Operation Rules
- **Silent Mode**: Internal calls between tools should use the `run_git_tool_managed` interface from `tool.GIT.logic.interface.main` to avoid output clutter.
- **Bold Phrases**: When reporting success, the entire action (e.g. "**Successfully pushed**") should be bolded.
- **Erasable Lines**: Always ensure progress lines are cleared or overwritten by final results to maintain a clean terminal history.

