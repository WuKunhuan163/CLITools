# GIT Tool

Standardized Git operations with managed execution and progress tracking.

## Features

- **Progress Display**: Real-time percentage display for push and pull operations using the root `logic.utils.run_with_progress` helper.
- **Branch Management**: Linear branch alignment logic (`dev` -> `tool` -> `main` -> `test`) used by the system-wide `TOOL dev sync` command.
- **Isolated Execution**: Inherits from `ToolBase` to ensure Git commands are executed within a managed environment if complex dependencies are required.
- **Erasable Status**: Clean terminal experience with blue bold progress indicators and green bold results.

## Usage

The `GIT` tool acts as a proxy for standard git commands while adding progress visualization:

```bash
GIT push origin dev
GIT checkout tool
GIT status
```

## Internal Architecture

The tool is organized into several modules:
- `logic/engine.py`: Core Git command execution and output parsing.
- `logic/interface/main.py`: Managed entry point for internal tool-to-tool calls.
- `main.py`: Primary CLI entry point.

## Ecosystem Integration

This tool provides the underlying Git synchronization logic for the entire `AITerminalTools` manager. It is a critical component for maintaining the linear development workflow.

