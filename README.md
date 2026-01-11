# AI Terminal Tools

## Vision
Empower AI Agents with more practical tools to improve the efficiency of collaborative development between AI and users (users themselves can also have a better workflow).

## Mission
Create these tools as modules and have a unified management mechanism.

## Quickstart

To get started quickly, follow these steps:

1. **Clone and Setup**:
   ```bash
   git clone https://github.com/WuKunhuan163/AITerminalTools.git
   cd AITerminalTools
   ./setup.py
   ```
   This registers the `TOOL` command. Restart your terminal or source your shell profile to apply changes.

2. **Install a Tool**:
   ```bash
   TOOL install USERINPUT
   ```
   This fetches the tool and its dependencies (like `PYTHON`) automatically.

3. **Experience the Tool**:
   ```bash
   USERINPUT --hint "Hello AI world!"
   ```
   Try running the tool directly. This is how your AI agent will communicate with you—by triggering a GUI for immediate feedback, bypassing the limitations of purely text-based interfaces.

4. **Enhance your Agent and Workflow**:
   ```bash
   TOOL rule
   ```
   Generate AI tool rules and integrate them into your environment. For example, in Cursor, you can copy the output to `Settings` -> `General` -> `Rules for AI`.
   
   **Note**: These tools are designed to be used by both AI agents and human developers. An agent using a tool to get your feedback (e.g., via `USERINPUT`) does not conflict with you using the same tool for your own tasks. They create a synchronized and efficient development experience.

## Mechanism

The project implements a lightweight yet powerful management system for AI-assisted development.

### Tool Acquisition & Isolation
Tools are not stored in the `main` branch to keep the root directory clean. Instead, they are fetched from a dedicated `tool` branch using `git checkout <branch> -- <path>`. This allows the repository to scale to hundreds of tools without cluttering the main workspace.

### Dependency Management
- **Standalone Runtime**: Tools can specify a dependency on the `PYTHON` tool. The manager ensures they run in a dedicated, isolated Python 3.10.19 environment.
- **Automated Pip Installation**: If a tool contains a `requirements.txt`, the manager automatically installs the necessary packages into the standalone runtime during the installation process.

### Unified Command Interface
The `TOOL` command provides a standardized interface for all tool-related operations:
- **`TOOL install <NAME>`**: Fetches the tool, installs dependencies, and creates a wrapper/shortcut in `bin/`.
- **`TOOL test <NAME>`**: Executes unit tests using a shared `TestRunner`. It supports parallel execution to speed up testing of complex tools.
- **`TOOL config set-lang <CODE>`**: Manages global preferences, such as switching the UI language for all tools.
- **`TOOL rule`**: Dynamically generates AI agent guidelines based on currently installed tools.

### Modular Architecture
Each tool follows a strict structure:
- `main.py`: CLI entry point.
- `proj/`: Core logic and `translations.json` for multi-language support.
- `test/`: Isolated unit tests using the `unittest` framework.
- `tool.json`: Metadata and dependency definitions.
