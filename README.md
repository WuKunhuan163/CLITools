# AITerminalTools

A robust, symmetrical, and user-friendly tool management system designed for AI agents and developers. It provides a standardized framework for building, deploying, and managing terminal-based tools with GUI support, multi-language localization, and isolated runtimes.

## Quick Start (Deployment Guide)

### 1. Initial Setup
Clone the repository and run the setup script to create the `TOOL` shortcut and add it to your `PATH`.

#### macOS / Linux
- Ensure `python3` and `git` are in your `PATH`.
- Clone the repository.
- Run `python3 setup.py`.

#### Windows
- Install Python from python.org and Git from git-scm.com.
- Ensure "Add Python to PATH" is checked during installation.
- Run `python setup.py` from PowerShell or Git Bash.

### 2. Install Your First Tool
Once setup is complete, you can use the `TOOL` command directly. The `USERINPUT` tool is highly recommended for obtaining interactive feedback from users.

```bash
TOOL install USERINPUT
```

### 3. Run the Tool
Now you can call the tool by its name from any terminal:

```bash
USERINPUT --hint "Hello! AITerminalTools is now operational."
```

---

## Key Features & Commands

### Tool Management
- `TOOL install <NAME>`: Installs a tool, its tool-dependencies, and its pip-dependencies. Generates a **Managed Bootstrap Shortcut** in `bin/` that automatically uses the correct isolated environment.
- `TOOL reinstall <NAME>`: Wipes and fresh-install a specific tool.
- `TOOL uninstall <NAME>`: Safely removes a tool and its shortcuts.
- `TOOL test <NAME>`: Runs a suite of unit tests in parallel. Every tool includes a mandatory `test_00_help.py` to ensure `--help` support is always functional. The manager includes a **CPU Wait Stage** to ensure stable results on overloaded systems. Tests can define an `EXPECTED_CPU_LIMIT` for individual stability. The runner automatically records your current branch and restores it after tests finish, ensuring your development environment remains consistent.
- `TOOL config`: Manages global configuration, including `--test-cpu-limit` and `--test-cpu-timeout`.
- `TOOL rule`: **Critical for AI Agents.** Generates a comprehensive set of rules and instructions that you can paste into your AI agent's system prompt or context. Use `TOOL <NAME> rule` for tool-specific guidelines.
- `TOOL clear`: Clears the terminal screen.
- `--no-warning`: Global flag to suppress non-critical system warnings (e.g., high CPU load).

### USERINPUT Tool
A core tool for human-in-the-loop AI workflows:
- **GUI Feedback**: Pop up a multi-line input window.
- **Remote Control**: Command-line based submission (`USERINPUT submit`), cancellation, and time extension (`USERINPUT add_time`).
- **Timed Interaction**: Default 300s timeout with automatic refocus and periodic bell (90s interval) to prevent missed feedback.
- **Sandbox Fallback**: Automatically switches to file-based input if GUI fails due to environment restrictions (e.g., macOS Seatbelt in Cursor, Docker).
- **Isolated Runtime**: Automatically uses the `PYTHON` tool to ensure a consistent execution environment.
- **Auto-Commit**: Automatically commits and pushes local changes before waiting for feedback to protect work progress.

### GIT Tool
Standardized Git operations with progress display:
- **Managed Execution**: `GIT <args>` runs git commands with blue erasable status and bold results.
- **Progress Tracking**: Real-time percentage display for push/pull operations.
- **Branch Management**: Refined branch alignment logic used by `TOOL dev sync`.
- **Dependency Management**: Automatically handles Python and library dependencies for complex Git workflows.

### FILEDIALOG Tool
Standardized file and directory selection:
- **Advanced Selection**: Supports batch selection via Shift/Cmd/Ctrl and range selection.
- **Smart Navigation**: Breadcrumb navigation with truncation and history management (back/forward).
- **Sorting**: Clickable headers for Name, Size, and Type sorting.
- **Symmetry**: Shares the same unified GUI and sandbox fallback infrastructure as `USERINPUT`.

### TEX Tool
Local LaTeX compilation and template manager (formerly `OVERLEAF`):
- **Compilation**: `TEX compile <file.tex>` to generate PDF locally.
- **Templates**: `TEX template <name>` to bootstrap projects for Nature, Science, ACM, IEEE, NeurIPS, and more.
- **Management**: Self-contained template storage and local TeX engine support.

### PYTHON Tool
The foundation for tool isolation:
- **Version Management**: `PYTHON --py-install 3.11.14` to deploy specific Python versions.
- **Environment Integration**: `PYTHON --enable` creates symlinks for `python` and `pip` in `bin/` pointing to the managed Python installation. These symlinks automatically resolve to the isolated environment, ensuring global `which python` and `which pip` commands work correctly across the project.
- **Terminal Reliability**: Automatically restores terminal echoing via `atexit` handlers even during `KeyboardInterrupt` or unexpected exits.
- **Dependency Isolation**: Ensures tools run with their own dedicated interpreters and pip environments.
- **Automatic Discovery**: Used by the `TOOL` ecosystem to resolve the correct runtime for each tool.

### SEARCH Tool
Multi-platform search for web and academic papers:
- **Web Search**: Fast, terminal-based search using DuckDuckGo.
- **Academic Search**: Parallel search across arXiv and Google Scholar with academic-specific filtering.
- **Preferences**: Support for sorting by citations, year, and relevance overlap.

### BACKGROUND Tool
Manage long-running tasks:
- **Non-blocking Execution**: Run time-consuming commands in the background.
- **Lifecycle Management**: List, stop, and wait for background processes.
- **Logging**: Automatically capture and view background output logs.

### GOOGLE.GCS Tool
Google Drive Remote Controller for Google Colab:
- **Remote Commands**: `GCS <command>` executes arbitrary commands remotely on Google Colab. Default generates bash scripts; use `--python` for Python cell scripts.
- **Path Expansion**: Unquoted `~` and `@` in commands are expanded to remote mount paths, respecting bash quoting rules. `GCS echo "~ is not '~'"` expands only unquoted occurrences.
- **Interactive Shell**: `GCS --shell` enters an interactive REPL where commands are automatically prefixed with `GCS`. Type `help` for available commands, `exit` to quit.
- **Path Management**: Virtual filesystem with `~` (remote root) and `@` (remote env). Use `GCS cd`, `GCS pwd`, and `GCS ls` to navigate Google Drive folders directly via the API.
- **Bash-like Exit Codes**: Commands return non-zero exit codes on failure (e.g., `ls` on nonexistent path prints `ls: cannot access '~/path': No such file or directory` to stderr and exits 1).
- **Non-Interactive API**: All file operations (`ls`, `cd`, `cat`) execute via isolated tmp scripts with IPv4-forced connections and automatic retry on transient errors.
- **GUI Queue**: GUI interaction windows are serialized via file-based FIFO locking, ensuring ordered execution when multiple commands require user interaction (e.g., `cd` then `echo >>`).
- **Remounting**: `GCS --remount` to quickly remount Google Drive in Colab with GUI and API-based verification.
- **Shell Management**: `GCS --shell list|switch|create|info` for stateful logical remote sessions.
- **Setup**: `GCS --setup-tutorial` for guided initial configuration of service account credentials and remote folders.
- **GUI Cancel**: Closing or cancelling a GCS GUI window exits the Turing Machine cleanly with a yellow "Cancelled." message.
- **Modular Architecture**: Command implementations are separated into `logic/command/` modules (ls, cd, pwd, cat, shell, remote, remount, tutorial). Core utilities in `logic/utils.py`.

### iCloudPD Tool
Standardized iCloud photo and video downloader:
- **Parallel Downloads**: Support for N-worker concurrent downloading (parameterized via `--workers`).
- **Dynamic Progress**: Single-line real-time progress showing current filenames and total completion.
- **Date Filtering**: Filter by `--since` and `--before` date ranges (YYYY-MM-DD).
- **Local Library Support**: Use `--local-photos [PATH]` to check a local Apple Photos Library (.photoslibrary) before downloading from iCloud. It maps iCloud IDs to local files using the database and resolves local creation times including timezone offsets. Supports offline gathering for locally-matched assets.
- **Custom Formatting**: Customize filenames and directories via `--prefix`, `--suffix`, and `--grouping`. Use placeholders like `<YYYY>`, `<MM>`, `<DD>`, `<hh>`, `<mm>`, `<ss>`, `<ID>`, and `<FILENAME>`.
- **Subtool Integration**: Operates as a subtool under the `iCloud` ecosystem, sharing authentication and 2FA interfaces.

### SKILLS Tool
Agent skill management for Cursor IDE:
- **Skill Library**: Manages a library of reusable AI agent skills in `tool/SKILLS/data/library/`.
- **Sync**: `SKILLS sync` creates symlinks from the library to `~/.cursor/skills/` for Cursor to discover.
- **Browse**: `SKILLS list` to see all available skills, `SKILLS show <name>` to view a skill's content.
- **Path**: `SKILLS path` to show the library directory path.

### Internationalization (i18n)
- `TOOL lang set <LANG>`: Sets the global display language (e.g., `zh` for Chinese, `en` for English, `ar` for Arabic).
- `TOOL lang list`: Shows supported languages and their translation coverage.
- `TOOL lang audit <LANG> [--turing]`: Deep audit of translation quality. Use `--turing` to also audit Turing Machine states across the codebase.
- `TOOL config`: Manages global configuration, including `--terminal-width` (use `auto` for dynamic detection), `--language`, and `--test-cpu-limit`.

### Developer Workflow
- `TOOL dev align`: One-click alignment of `tool`, `main`, and `test` branches with your current `dev` work. Includes a **Persistence Manager** that automatically saves and restores non-Git-tracked directories (like Python installations) across branch switches.
- `TOOL dev create <NAME>`: Generates a standardized tool template with unit tests and translation placeholders.
- `TOOL dev audit-test <NAME> [--fix]`: Audits unit test naming conventions. Every tool must have a `test_00_help.py`.
- `TOOL dev audit-bin [--fix]`: Validates that all shortcuts in `bin/` are healthy managed bootstrap scripts. Use `--fix` to automatically upgrade legacy symlinks or create missing shortcuts.
- `TOOL dev sanity-check <NAME>`: Verifies tool structure and required files.
- **Tool Config**: Use `TOOL_NAME config --cpu-limit <float>` to set per-tool resource constraints.
- **Nested Tooling**: Native support for subtools (e.g. `tool/PARENT.SUBTOOL/`). `ToolBase` robustly resolves paths and namespaces.

---

## Symmetry and Architecture

AITerminalTools follows a **Symmetrical Design Pattern**:
- The **Root** has a `logic/` folder for shared utilities (`logic.turing`, `logic.utils`, etc.).
- Each **Tool** (e.g., `tool/USERINPUT/`) also has its own `logic/` folder for tool-specific logic.
- Shadowing is avoided via intelligent `sys.path` management in each tool's entry point, ensuring `from logic...` always finds the root logic, while tool-specific logic is accessed via absolute paths or direct file reference.

### Core Directories
- `logic/`: Shared core logic, utilities, and global configuration.
- `tool/`: The home for all individual tools.
- `bin/`: Executable symlinks for installed tools.
- `resource/`: Large files and binaries (managed via Git LFS).
- `data/`: User settings, logs, and GUI instance registry.

### Unified Logging
Every tool has a built-in session logger accessible via `tool.log(message)`. Each invocation creates a single log file (`log_YYYYMMDD_HHMMSS_PID.log`) in the tool's `data/log/` directory. Log entries include timestamps, brief call stacks, and optional detail strings. Unhandled exceptions are automatically written to the same session log via `handle_exception()`. Log files are auto-cleaned when the count exceeds 64 (oldest half deleted).

---

## isolated Runtimes

Many tools depend on specific versions of Python or complex libraries. The `PYTHON` tool within this ecosystem manages isolated Python environments. When a tool specifies `PYTHON` as a dependency in its `tool.json`, the manager ensures it runs using the correct interpreter, preventing "dependency hell".

---

## Contribution

Active development happens on the `dev` branch. For detailed information on building new tools, refer to the **[Development Guide](logic/tool/template/README.md)** and the **[GUI Architecture](report/gui_architecture.md)**.


