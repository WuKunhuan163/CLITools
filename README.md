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
Once setup is complete, you can use the `TOOL` command directly. Every tool, once installed, becomes a **standalone terminal command** — its executable is placed in `bin/<TOOL_NAME>/` and automatically added to your system `PATH`. This is the core design: tools are CLI-first and callable directly from any terminal.

```bash
TOOL install USERINPUT
```

### 3. Run the Tool
After installation, call any tool by its name directly from the terminal:

```bash
USERINPUT --hint "Hello! AITerminalTools is now operational."
```

This works because `setup.py` adds `bin/` to your `PATH`. Each tool's executable at `bin/<NAME>/<NAME>` bootstraps the project environment and delegates to `tool/<NAME>/main.py`. This mechanism is universal — **every installed tool** follows the same pattern: `TOOL_NAME [--flags] [command] [args]`.

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

All Chrome-based tools use CDMCP session management with visual effects, auto-lock, idle timeout tracking, and max-session limits. See `SKILLS show cdmcp-web-exploration` for the development methodology.

### Specialized Tools

| Tool | Description |
|------|-------------|
| **GOOGLE.GDS** | Google Drive Remote Controller for Colab. Path expansion (`~`, `@`), file upload, interactive shell, GUI queue. |
| **iCloudPD** | Parallel iCloud photo/video downloader with date filtering and local library support. |

### SKILLS Tool
Manages AI agent skills, marketplace access, and evolution system:

**Skill Management:**
- `SKILLS list` / `SKILLS show <name>` / `SKILLS sync` — Browse, view, and link skills.

**Marketplace** (3000+ community skills from ClawHub/OpenClaw):
- `SKILLS market browse` — Top downloaded skills.
- `SKILLS market search <query>` — Search the marketplace.
- `SKILLS market install <slug>` — Download to `skills/marketplace/`.

**Evolution System** (self-improvement loop):
- `SKILLS learn / lessons / analyze / suggest / apply / history` — Full introspection cycle.
- Brain data stored in `runtime/experience/` (Git-tracked).

Available skills: `tool-development-workflow`, `turing-machine-development`, `setup-tutorial-creation`, `code-quality-review`, `session-debug-log`, `tmp-test-script`, `cdmcp-web-exploration`, `mcp-development`, `unit-test-conventions`, `localization`, `record-cache`, `tool-interface`, `skills-index`, `openclaw`. Run `SKILLS show <name>` for guidance.

### Internationalization (i18n)
- `TOOL lang set <LANG>`: Set display language.
- `TOOL lang audit <LANG> [--turing]`: Audit translation coverage.

### Semantic Search (Agent Exploration)
- `TOOL --search tools <query>`: Find tools by natural language (e.g. "open a Chrome tab").
- `TOOL --search interfaces <query>`: Find tool interfaces by functionality.
- `TOOL --search skills <query> [--tool NAME]`: Find skills, optionally scoped to a tool.
- `SKILLS search <query> [--tool NAME]`: Search skills from within the SKILLS tool.

Agents explore the project using these commands. Discoveries populate the agent's
environment (visible tools, interfaces, skills) for subsequent turns.

### Developer Workflow
- `TOOL --dev sync`: Align all branches (dev -> tool -> main -> test) with persistence management.
- `TOOL --dev create <NAME>`: Scaffold a new tool from template.
- `TOOL --dev audit-test <NAME> [--fix]`: Audit test naming conventions.
- `TOOL --dev audit-bin [--fix]` / `TOOL --dev audit-archived`: Audit shortcuts and archived tool duplicates.
- `TOOL --audit imports [--tool NAME] [--json]`: Static analysis for cross-tool import quality (IMP001-IMP004).
- `TOOL --audit quality [--tool NAME] [--json]`: Hooks, interface, and skills validation (HOOK001-HOOK006, IFACE001-IFACE005, SKILL001-SKILL003).

For detailed development guidance, run `SKILLS show tool-development-workflow`.

---

## Symmetry and Architecture

AITerminalTools follows a **Symmetrical Design Pattern**:
- The **Root** has a `logic/` folder for shared utilities and an `interface/` facade layer that re-exports stable symbols for tool consumption.
- **Tools** import from `interface.*` (e.g., `from interface.status import fmt_status`), never directly from `logic.*`.
- Each **Tool** (e.g., `tool/USERINPUT/`) also has its own `logic/` folder for tool-specific **internal** implementation.
- Each **Tool** exposes a public API via `interface/main.py` at the tool root. Cross-tool imports MUST go through the interface.
- Shadowing is avoided via intelligent `sys.path` management in each tool's entry point, ensuring `from logic...` always finds the root logic, while tool-specific logic is accessed via absolute paths or direct file reference.

### Core Directories
- `logic/`: Shared core logic, utilities, and global configuration. Internal implementation — tools should not import from `logic.*` directly.
- `interface/`: Stable facade layer. Re-exports key symbols from `logic/` for tool consumption. Tools import from `interface.*` (e.g., `from interface.status import fmt_status`). See `interface/for_agent.md`.
- `tool/`: The home for all active tools. Each tool has:
  - `logic/` — Internal implementation (not for cross-tool access).
  - `interface/` — Public API for cross-tool communication.
  - `hooks/` — Event-driven callback interfaces and instances.
- `bin/`: Executable symlinks for installed tools.
- `resource/tool/`: Large binary assets (fonts, Python builds) — only on the `tool` branch.
- `resource/archived/`: Archived/unmaintained tools — only on the `tool` branch. `TOOL install` falls back here.
- `data/`: Transient runtime data (gitignored) — caches, logs, GUI state.
- `runtime/`: Tracked runtime data (git-tracked) — institutional memory.
  - `runtime/experience/`: Agent's cross-tool experience (lessons, suggestions, evolution history).
- `skills/`: AI agent skill documents, organized under `core/` and `AI-IDE/`.
- `research/`: Research notes and analysis documents.

> **Note**: The `.gitignore` is auto-generated by `GitIgnoreManager` in `logic/git/manager.py`. Never edit it directly — add new directories to `GitIgnoreManager.base_patterns` instead.

### Unified Logging
Every tool has a built-in session logger via `tool.log(message)`. Log files auto-clean when count exceeds 64. Run `SKILLS show session-debug-log` for logging patterns.

---

## For AI Agents

**If you are an AI agent** (LLM assistant, IDE copilot, or automated system), read `for_agent.md` in this directory for comprehensive architecture docs, tool conventions, and the AI IDE integration workflow. That file is your primary reference.

Key entry points:
- `for_agent.md` — Full architecture guide, tool conventions, agent bootstrap, AI IDE workflow
- `TOOL --search all "<query>"` — Semantic search across all tools, skills, lessons
- `TOOL --session --agent/--ask/--plan --self-operate --prompt "<task>"` — Start a self-operate session (choose mode by task type)
- `USERINPUT` — Get interactive user feedback

### AI IDE Integration (Self-Operate Mode)

AI IDE agents (Cursor, Copilot, Windsurf, etc.) can use `--self-operate` mode to drive development through this project's assistant infrastructure. The project complements the IDE — it provides session tracking, an HTML GUI, quality nudges, and tool orchestration while the IDE handles file editing and code navigation.

```bash
# Quick start: choose --agent (full access), --ask (read-only), or --plan (design)
TOOL --session --agent --prompt "<task>" --self-operate --self-name "Model" --env "IDE/cursor"
TOOL --agent response <SID> tmp/response.json    # Inject response (auto-feeds next round)
TOOL --agent response <SID> '[{"type":"complete","reason":"done"}]'   # Complete
```

See `for_agent.md` sections "Self-Operate Mode" and "AI IDE Integration Workflow" for the full guide, response JSON format, and lifecycle rules.

### Remote Assistant Integration

When a remote LLM provider acts as the assistant, the system manages the full conversation loop: context packaging, tool execution, quality checks, and GUI rendering. Both remote-provider and self-operate sessions share the same lifecycle (running → done), GUI visualization, and tool execution pipeline.

---

## Contribution

Active development happens on the `dev` branch. Run `SKILLS show tool-development-workflow` for the full development guide.


