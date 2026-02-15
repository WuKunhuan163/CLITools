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
- `TOOL test <NAME>`: Runs a suite of unit tests in parallel. Every tool includes a mandatory `test_00_help.py` to ensure `--help` support is always functional.
- `TOOL rule`: **Critical for AI Agents.** Generates a comprehensive set of rules and instructions that you can paste into your AI agent's system prompt or context. Use `TOOL <NAME> rule` for tool-specific guidelines.
- `TOOL clear`: Clears the terminal screen.

### USERINPUT Tool
A core tool for human-in-the-loop AI workflows:
- **GUI Feedback**: Pop up a multi-line input window.
- **Remote Control**: Command-line based submission (`USERINPUT submit`), cancellation, and time extension (`USERINPUT add_time`).
- **Timed Interaction**: Default 300s timeout with automatic refocus and periodic bell (90s interval) to prevent missed feedback.
- **Sandbox Fallback**: Automatically switches to file-based input if GUI fails due to environment restrictions (e.g., macOS Seatbelt in Cursor, Docker).
- **Isolated Runtime**: Automatically uses the `PYTHON` tool to ensure a consistent execution environment.

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

### iCloudPD Tool
Standardized iCloud photo and video downloader:
- **Parallel Downloads**: Support for N-worker concurrent downloading (parameterized via `--workers`).
- **Dynamic Progress**: Single-line real-time progress showing current filenames and total completion.
- **Date Filtering**: Filter by `--since` and `--before` date ranges (YYYY-MM-DD).
- **Subtool Integration**: Operates as a subtool under the `iCloud` ecosystem, sharing authentication and 2FA interfaces.

### Internationalization (i18n)
- `TOOL lang set <LANG>`: Sets the global display language (e.g., `zh` for Chinese, `en` for English, `ar` for Arabic).
- `TOOL lang list`: Shows supported languages and their translation coverage.
- `TOOL lang audit <LANG>`: Deep audit of translation quality, detecting missing keys, duplicate values, shadowed core keys, and unused entries.

### Developer Workflow
- `TOOL dev align`: One-click alignment of `tool`, `main`, and `test` branches with your current `dev` work.
- `TOOL dev create <NAME>`: Generates a standardized tool template with unit tests and translation placeholders.
- `TOOL dev audit-bin [--fix]`: Validates that all shortcuts in `bin/` are healthy managed bootstrap scripts. Use `--fix` to automatically upgrade legacy symlinks or create missing shortcuts.
- `TOOL dev sanity-check <NAME>`: Verifies tool structure and required files.
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

---

## isolated Runtimes

Many tools depend on specific versions of Python or complex libraries. The `PYTHON` tool within this ecosystem manages isolated Python environments. When a tool specifies `PYTHON` as a dependency in its `tool.json`, the manager ensures it runs using the correct interpreter, preventing "dependency hell".

---

## Contribution

Active development happens on the `dev` branch. For detailed information on building new tools, refer to the **[Development Guide](logic/tool/template/README.md)** and the **[GUI Architecture](report/gui_architecture.md)**.


