# AITerminalTools

A robust and user-friendly tool management system for AI agents.

## Prerequisites

Before using AITerminalTools, ensure you have the following installed:

1.  **Python 3.7+**: The core system runs on Python. 
    - *Note*: The `PYTHON` tool within this ecosystem can manage multiple isolated Python versions for other tools, but a base Python installation is required to run the manager itself.
2.  **Git**: Required for tool installation, updates, and branch management.

### Deployment Guide

#### macOS / Linux
- Ensure `python3` and `git` are in your `PATH`.
- Clone the repository.
- Run `python3 main.py install <TOOL_NAME>` to get started.

#### Windows
- Install Python from python.org and Git from git-scm.com.
- Ensure "Add Python to PATH" is checked during installation.
- Use a terminal like PowerShell or Git Bash.
- Run `python main.py install <TOOL_NAME>`.

## Key Commands

- `TOOL install <NAME>`: Install a tool and its dependencies.
- `TOOL uninstall <NAME>`: Safely remove a tool.
- `TOOL test <NAME>`: Run unit tests for a tool.
- `TOOL rule`: Generate instructions for AI agents.
- `TOOL lang set <LANG>`: Change the system language (e.g., `zh`, `en`, `ar`).
- `TOOL sync`: Synchronize development work across branches.

## Documentation

- **[GUI Architecture](report/gui_architecture.md)**: Details on the unified GUI blueprint, State-Interface model, and registry-based termination.
- **[Development Guide](logic/tool/template/README.md)**: Information on creating and migrating new tools.

## Architecture

- **`logic/`**: Shared core logic, utilities, and global configuration.
- **`tool/`**: Directory containing all available tools.
- **`bin/`**: Executable wrappers for installed tools.
- **`data/`**: User data, logs, and temporary files.

## Development

Active development happens on the `dev` branch. The `tool` branch is used for resource migration and distribution. The `main` and `test` branches are kept clean for production and verification.

For more information on creating new tools, see `logic/tool/template/README.md`.
