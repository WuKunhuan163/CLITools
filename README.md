# AI Terminal Tools

## Vision
Empower AI Agents with more practical tools to improve the efficiency of collaborative development between AI and users (users themselves can also have a better workflow).

## Mission
Create these tools as modules and have a unified management mechanism.

## Quickstart

To get started quickly, follow these steps:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/WuKunhuan163/AITerminalTools.git
   cd AITerminalTools
   ```

2. **Run setup**:
   ```bash
   ./setup.py
   ```
   This will register the `TOOL` command in your shell profile. You may need to restart your terminal or run `source ~/.zshrc` (or equivalent).

3. **Explore and use tools**:
   - **Install a tool**: `TOOL install USERINPUT`
   - **List installed tools**: `TOOL list` (or just check the `tool/` directory)
   - **Change language**: `TOOL config set-lang zh` (to switch to Chinese)
   - **Generate AI Rules**: `TOOL rule` (generate guidelines for your AI agents)

The goal is to provide a seamless workflow where you can quickly install tools and equip your AI agents with the necessary rules to use them effectively.

## Mechanism

The project uses a modular management system driven by `main.py` and `setup.py`.

### Core Mechanism
- **`setup.py`**: Project deployment script. It creates a `TOOL` shortcut in your terminal that points to `main.py` and ensures it's persistently available in your shell profiles.
- **`main.py`**: The central tool manager.
  - `TOOL install <NAME>`: Fetches the tool from the `tool` branch, installs its dependencies (including `PYTHON` and `pip` packages), and creates a wrapper script in the `bin/` directory.
  - `TOOL test <NAME>`: Runs unit tests for the specified tool.
  - `TOOL rule`: Generates a comprehensive set of rules for AI agents to understand how to use the installed tools.
  - `TOOL config set-lang <CODE>`: Sets the global language preference for all tools.

### Tool Architecture
Each tool is a self-contained module in its own directory (e.g., `tool/USERINPUT/`):
- `main.py`: Entry point for the tool.
- `proj/`: Source code and localized translations (`translations.json`).
- `test/`: Unit tests based on the `unittest` framework.
- `tool.json`: Metadata defining purpose, description, and dependencies.
- `README.md`: Tool-specific documentation.

### Testing Framework
The `TOOL test` mechanism uses a shared `TestRunner` in the root `proj/` folder. It discovers all `test_*.py` files within a tool's `test/` directory and executes them in a clean environment. For multi-test execution, it can leverage the `BACKGROUND` tool to run tests in parallel, significantly reducing testing time for complex tools like `GOOGLE_DRIVE`.

### Standalone Python Environment
To ensure maximum compatibility and avoid dependency conflicts, tools can depend on the `PYTHON` tool. The manager automatically ensures that these tools run within a dedicated Python 3.10.19 environment, complete with its own set of pre-installed libraries and `pip` dependencies.
