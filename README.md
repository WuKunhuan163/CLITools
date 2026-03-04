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
- `TOOL install <NAME>`: Installs a tool (searches dev/tool branches, falls back to `resource/archived/`).
- `TOOL reinstall <NAME>` / `TOOL uninstall <NAME>`: Wipe-reinstall or remove a tool.
- `TOOL test <NAME>`: Runs unit tests in parallel with CPU monitoring and branch restoration.
- `TOOL status`: Shows all registered tools with installation status, configuration completeness, and test counts.
- `TOOL config show`: Displays all global and per-tool configurations.
- `TOOL config set <key> <value>`: Sets a global configuration value.
- `TOOL rule`: Generates AI agent context rules. Use `TOOL <NAME> rule` for tool-specific guidelines.
- `--no-warning`: Suppresses non-critical system warnings.

### Core Tools

| Tool | Description |
|------|-------------|
| **USERINPUT** | GUI feedback window for human-in-the-loop AI workflows. Auto-commit, sandbox fallback, remote control. |
| **GIT** | Git wrapper with progress display and branch management. |
| **FILEDIALOG** | Advanced file/directory selection with batch selection and breadcrumb navigation. |
| **TEX** | Local LaTeX compilation and journal templates (Nature, Science, ACM, IEEE, NeurIPS). |
| **PYTHON** | Isolated Python runtime management. Version install, symlink creation, dependency isolation. |
| **SEARCH** | Multi-platform search (DuckDuckGo, arXiv, Google Scholar). |
| **BACKGROUND** | Background process management with logging and lifecycle control. |
| **TAVILY** | AI-optimized web search via Tavily API. `TAVILY --setup-tutorial` for guided configuration. |

### Chrome DevTools MCP Tools

| Tool | Description |
|------|-------------|
| **GOOGLE.CDMCP** | Chrome DevTools MCP: session management, visual overlays, tab pinning, lock/unlock, MCP interaction interfaces (`mcp_click`, `mcp_type`, `mcp_navigate`, `mcp_scroll`, `mcp_paste`). Provides `boot_tool_session()` and `require_tab()` for all Chrome-based tools. |
| **GOOGLE.GC** | Google Colab automation: cell CRUD, edit, run, focus, move, delete, runtime management, notebook save/clear, Turing machine state. |
| **YOUTUBE** | YouTube MCP: playback control, search, navigation, captions, engagement, recommendations, state reporting. |
| **BILIBILI** | Bilibili MCP: video playback, search, comments (shadow DOM), danmaku, engagement, state machine recovery. |
| **GMAIL** | Gmail MCP: inbox reading, compose, label management, search. (In development) |
| **GOOGLE.GS** | Google Scholar MCP: search, citations, profiles, library. (In development) |

All Chrome-based tools use CDMCP session management with visual effects, auto-lock, idle timeout tracking, and max-session limits. See `SKILLS show TerminalTools-cdmcp-web-exploration` for the development methodology.

### Specialized Tools

| Tool | Description |
|------|-------------|
| **GOOGLE.GCS** | Google Drive Remote Controller for Colab. Path expansion (`~`, `@`), file upload, interactive shell, GUI queue. |
| **iCloudPD** | Parallel iCloud photo/video downloader with date filtering and local library support. |

### SKILLS Tool
Manages reusable AI agent skills for Cursor IDE:
- `SKILLS list`: Browse available skills.
- `SKILLS show <name>`: View a skill's content.
- `SKILLS sync`: Link skills to `~/.cursor/skills/`.

Available skills: `TerminalTools-tool-development-workflow`, `TerminalTools-turing-machine-development`, `TerminalTools-setup-tutorial-creation`, `TerminalTools-code-quality-review`, `TerminalTools-session-debug-log`, `TerminalTools-tmp-test-script`, `TerminalTools-cdmcp-web-exploration`, `TerminalTools-unit-test-conventions`. Run `SKILLS show <name>` for detailed guidance.

### Internationalization (i18n)
- `TOOL lang set <LANG>`: Set display language.
- `TOOL lang audit <LANG> [--turing]`: Audit translation coverage.

### Developer Workflow
- `TOOL dev sync`: Align all branches (dev → tool → main → test) with persistence management.
- `TOOL dev create <NAME>`: Scaffold a new tool from template.
- `TOOL dev audit-test <NAME> [--fix]`: Audit test naming conventions.
- `TOOL dev audit-bin [--fix]` / `TOOL dev audit-archived`: Audit shortcuts and archived tool duplicates.
- `TOOL audit imports [--tool NAME] [--json]`: Static analysis for cross-tool import quality (IMP001-IMP004).
- `TOOL audit quality [--tool NAME] [--json]`: Hooks, interface, and skills validation (HOOK001-HOOK006, IFACE001-IFACE005, SKILL001-SKILL003).

For detailed development guidance, run `SKILLS show TerminalTools-tool-development-workflow`.

---

## Symmetry and Architecture

AITerminalTools follows a **Symmetrical Design Pattern**:
- The **Root** has a `logic/` folder for shared utilities (`logic.turing`, `logic.utils`, etc.).
- Each **Tool** (e.g., `tool/USERINPUT/`) also has its own `logic/` folder for tool-specific **internal** implementation.
- Each **Tool** exposes a public API via `interface/main.py` at the tool root. Cross-tool imports MUST go through the interface.
- Shadowing is avoided via intelligent `sys.path` management in each tool's entry point, ensuring `from logic...` always finds the root logic, while tool-specific logic is accessed via absolute paths or direct file reference.

### Core Directories
- `logic/`: Shared core logic, utilities, and global configuration.
- `tool/`: The home for all active tools. Each tool has:
  - `logic/` — Internal implementation (not for cross-tool access).
  - `interface/` — Public API for cross-tool communication.
  - `hooks/` — Event-driven callback interfaces and instances.
- `bin/`: Executable symlinks for installed tools.
- `resource/tool/`: Large binary assets (fonts, Python builds) — only on the `tool` branch.
- `resource/archived/`: Archived/unmaintained tools — only on the `tool` branch. `TOOL install` falls back here.
- `data/`: User settings, logs, and GUI instance registry.

### Unified Logging
Every tool has a built-in session logger via `tool.log(message)`. Log files auto-clean when count exceeds 64. Run `SKILLS show TerminalTools-session-debug-log` for logging patterns.

---

## Contribution

Active development happens on the `dev` branch. Run `SKILLS show TerminalTools-tool-development-workflow` for the full development guide.


