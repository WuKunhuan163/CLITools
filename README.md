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
- `TOOL install <NAME>`: Installs a tool, its tool-dependencies, and its pip-dependencies.
- `TOOL uninstall <NAME>`: Safely removes a tool and its shortcuts.
- `TOOL test <NAME>`: Runs a suite of unit tests in parallel. Highly optimized for speed and reliability.
- `TOOL rule`: **Critical for AI Agents.** Generates a comprehensive set of rules and instructions that you can paste into your AI agent's system prompt or context. Use `TOOL <NAME> rule` for tool-specific guidelines.
- `TOOL clear`: Clears the terminal screen.

### USERINPUT Tool
A core tool for human-in-the-loop AI workflows:
- **GUI Feedback**: Pop up a multi-line input window.
- **Remote Control**: Command-line based submission (`USERINPUT submit`), cancellation, and time extension (`USERINPUT add_time`).
- **Timed Interaction**: Default 300s timeout with automatic refocus and periodic bell (90s interval) to prevent missed feedback.
- **Isolated Runtime**: Automatically uses the `PYTHON` tool to ensure a consistent execution environment.

### PYTHON Tool
The foundation for tool isolation:
- **Version Management**: `PYTHON --py-install 3.11.14` to deploy specific Python versions.
- **Dependency Isolation**: Ensures tools run with their own dedicated interpreters and pip environments.
- **Automatic Discovery**: Used by the `TOOL` ecosystem to resolve the correct runtime for each tool.

### Internationalization (i18n)
- `TOOL lang set <LANG>`: Sets the global display language (e.g., `zh` for Chinese, `en` for English, `ar` for Arabic).
- `TOOL lang list`: Shows supported languages and their translation coverage.
- `TOOL lang audit <LANG>`: Audits the codebase for missing translations in a specific language.

### Developer Workflow
- `TOOL dev align`: One-click alignment of `tool`, `main`, and `test` branches with your current `dev` work. It automatically handles uncommitted changes and cleans up restricted directories.
- `TOOL dev enter <main|test>`: Safely switches to production or testing branches, automatically cleaning up untracked files.
- `TOOL dev create <NAME>`: Generates a standardized tool template with logic, translations, and unit tests.
- `TOOL dev audit-bin`: Ensures that the `bin/` directory only contains pure symlinks (except for the `TOOL` manager itself).

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
