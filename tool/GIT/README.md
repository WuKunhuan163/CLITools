# GIT Tool

Standardized Git operations with managed execution and progress tracking.

## Features

- **Progress Display**: Real-time percentage display for push and pull operations using the root `logic.utils.run_with_progress` helper.
- **Linear Branch Management**: Linear branch alignment logic (`dev` -> `tool` -> `main` -> `test`) used by the system-wide `TOOL dev sync` command.
- **History Maintenance**: Automated commit squashing mechanism to keep the repository history lean and reduce LFS storage costs.
- **Rolling Auto-Commits**: Integration with `USERINPUT` for automatic progress saving with rolling `#xxxx` tags.

## Usage

### Standard Operations
The `GIT` tool acts as a proxy for standard git commands while adding progress visualization:

```bash
GIT push origin dev
GIT checkout tool
GIT status
```

### History Maintenance
Manually trigger history optimization:

```bash
GIT maintain --base 50
```

## History Maintenance Model

The maintenance system uses a tiered frequency model based on a `base` commit count:
1. **Safe Zone**: The last `base` commits are always kept intact.
2. **Maintenance Zone**: Commits older than `base` are squashed based on levels:
   - **Level 2 (2*base)**: Interval where every 2 commits are merged into 1 (Frequency 0.5).
   - **Level 12 (12*base)**: Interval where every 12 commits are merged into 1 (Frequency 1/12).
   - **Level 120 (120*base)**: Interval where every 120 commits are merged into 1 (Frequency 1/120).

**Constraint**: `base * level * frequency` must be an integer to ensure clean chunks.

## Internal Architecture

The tool is organized into several modules:
- `logic/engine.py`: Core Git command execution and output parsing.
- `interface/main.py`: Managed entry point for internal tool-to-tool calls.
- `main.py`: Primary CLI entry point.

## Ecosystem Integration

This tool provides the underlying Git synchronization logic for the entire `AITerminalTools` manager. It is a critical component for maintaining the linear development workflow.

