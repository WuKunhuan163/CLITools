# AITerminalTools: Guide for AI Agents

Welcome to the `AITerminalTools` ecosystem. This guide is designed to provide you with the essential context and technical framework needed to develop, maintain, and interact with tools in this project.

## 1. Core Philosophy: Symmetry & Automation
This project follows a **Symmetrical Design Pattern**. Shared core logic resides in the root `logic/` folder, a stable facade layer at `interface/` re-exports key symbols for tools, and each tool (located in `tool/`) has its own `logic/` directory for tool-specific implementations.

- **Isolation**: Use the `PYTHON` tool dependency to run your tool in a standalone runtime.
- **Persistence**: Work is automatically committed and pushed every few commits via git hooks to protect progress.
- **Persistence Manager**: `GitPersistenceManager` automatically saves and restores non-Git-tracked directories across branch switches during `TOOL dev sync` and `TOOL test`. Tools declare which directories to preserve via `"persistence_dirs": ["data"]` in their `tool.json`. This is critical for API keys, session cookies, and configs that live in `data/` on the dev branch.

### Import Convention: `interface/` Facade Layer
Tools MUST import shared utilities from `interface.*`, NOT directly from `logic.*`. The `interface/` directory re-exports stable symbols from `logic/` internals:

```python
from interface.status import fmt_status, fmt_warning, fmt_info
from interface.utils import preflight, retry, cleanup_old_files, SessionLogger
from interface.config import get_color
from interface.tool import ToolBase
from interface.turing import ProgressTuringMachine, TuringStage
from interface.audit import run_full_audit, print_report
```

See `interface/for_agent.md` for the full module map. Direct `logic.*` imports are only for code inside `logic/` itself.

### Symmetric Root Directories
Each tool (and the project root) shares these directory semantics:
- **`data/`**: Transient runtime data (gitignored). Caches, logs, session artifacts.
- **`runtime/`**: Tracked runtime data (git-tracked). Institutional memory, evolution history.
  - `runtime/experience/` at the project root holds the agent's cross-tool experience (lessons, suggestions, evolution history).
  - Individual tools can have their own `runtime/` for tool-specific tracked runtime data.
- **`logic/`**: Implementation code (shared at root, tool-specific under `tool/<NAME>/logic/`).
- **`interface/`**: Stable facade layer. Re-exports from `logic/` for external consumers (tools, skills, rules). See `interface/for_agent.md`.
- **Managed Python Environment**: Use `PYTHON --enable` to create symlinks in `bin/` so that `which python` and `pip install` use the managed environment correctly.
- **Terminal Restoration**: The `KeyboardSuppressor` uses `atexit` to ensure terminal echoing is restored even if the process exits unexpectedly or via `KeyboardInterrupt`.

## 2. Standard Tool Structure
Every tool MUST be created using `TOOL --dev create <NAME>`. Run `SKILLS show tool-development-workflow` for the full development guide.

### Tool Directory Layout
```text
tool/<NAME>/           # e.g., tool/iCloud/ or tool/iCloud.iCloudPD/
  ├── logic/           # Internal logic
  │   └── translation/ # Localization (zh.json, ar.json, etc.)
  ├── main.py          # Entry point (inherits from ToolBase)
  ├── setup.py         # Installation logic
  ├── tool.json        # Metadata, dependencies, persistence_dirs (see below)
  ├── test/            # Tool-specific unit tests (test_xx_name.py)
  └── README.md        # Documentation
```

## 3. The Tool Blueprint (`ToolBase`)
All tools inherit from `logic.tool.base.ToolBase`. Key features:
- **`handle_command_line(parser, dev_handler, test_handler)`**: Standardizes argument processing. Handles `setup`, `install`, `uninstall`, `rule`, `config`, `skills`, `--dev`, `--test`, `--agent`, `--ask`, `--plan` commands automatically. Custom `dev_handler` and `test_handler` callbacks can extend the built-in developer commands.
- **`--dev` Support**: Every tool supports `TOOL_NAME --dev <command>`. Built-in commands: `sanity-check [--fix]`, `audit-test [--fix]`, `info`. Tools can pass a custom `dev_handler` to `handle_command_line()` for tool-specific dev commands.
- **`--test` Support**: Every tool supports `TOOL_NAME --test [options]`. Runs the tool's unit tests with `--range`, `--max`, `--timeout`, `--list` options.
- **`--agent`/`--ask`/`--plan` Support**: Every tool supports three agent modes. `--agent` (full), `--ask` (read-only), `--plan` (read-only + no scripts). See Agent Mode section below.
- **Help Support**: Every tool MUST support `-h` and `--help`.
- **Python Runtime**: If `PYTHON` is a dependency, ToolBase ensures the isolated Python environment is used.
- **System Fallback**: Unrecognized commands delegate to system equivalents (e.g., `GIT` → `/usr/bin/git`).
- **CPU Monitoring**: Automatic CPU load check with configurable threshold and warning.
- **Programmatic Interface**: `--tool-quiet` returns results as `TOOL_RESULT_JSON:...` for machine consumption.
- **Unified Success**: `self.raise_success_status("action")` for green-bold **Successfully [action]** messages.
- **Path Resolution**: Use `self.tool_dir`, `self.get_data_dir()`, `self.get_log_dir()`. See also the Universal Path Resolver below.

## 4. Branch Synchronization & Alignment
This project uses a linear four-stage branch strategy: `dev -> tool -> main -> test`.
- **`dev`**: Active development branch. Does NOT contain `resource/` (gitignored).
- **`tool`**: Staging branch for tool testing. Contains `resource/tool/` (binary assets like fonts, Python builds) and `resource/archived/` (archived tools). The `resource/` directory is preserved from the previous tool branch during sync.
- **`main`**: Production-ready framework only (no `tool/`, `resource/`, `data/`, `bin/`, `tmp/`).
- **`test`**: Branch used for automated unit testing (mirrors tool).

### Tool Installation Sources
`TOOL install <NAME>` searches for tool source in this order:
1. Local `tool/<NAME>/main.py` (already exists)
2. Git branches: `dev`, `tool`, `origin/tool`, `origin/dev` → `tool/<NAME>/`
3. Fallback: `tool`/`origin/tool` → `resource/archived/<NAME>/` (copied to `tool/<NAME>/`)

### Synchronization & Developer Commands
Both `TOOL dev <command>` (legacy) and `TOOL --dev <command>` (preferred) syntax are supported:
- **`TOOL --dev sync`**: The primary command to synchronize all branches.
- **`TOOL --dev create <name>`**: Create a new tool from template.
- **`TOOL --dev sanity-check <name> [--fix]`**: Check tool structure integrity.
- **`TOOL --dev audit-test <name> [--fix]`**: Audit unit test naming.
- **`TOOL --dev audit-bin [--fix]`**: Audit bin/ shortcut structure.
- **`TOOL --dev audit-archived`**: Check for duplicate tools.
- **`TOOL audit imports [--tool NAME] [--json]`**: Static analysis for cross-tool import quality (IMP001-IMP004).
- **`TOOL audit quality [--tool NAME] [--json]`**: Hooks, interface, and skills validation (HOOK001-HOOK006, IFACE001-IFACE005, SKILL001-SKILL003).
- **`TOOL --dev enter <main|test> [-f]`**: Switch to branch.
- **`TOOL --dev migrate-bin`**: Migrate legacy flat bin/ shortcuts.

Per-tool developer commands (available for every tool via ToolBase):
- **`TOOL_NAME --dev sanity-check [--fix]`**: Check this tool's structure.
- **`TOOL_NAME --dev audit-test [--fix]`**: Audit this tool's test naming.
- **`TOOL_NAME --dev info`**: Show tool paths, dependencies, and test count.

Testing commands (both styles supported):
- **`TOOL --test <name>`** or **`TOOL_NAME --test`**: Run unit tests.
- **`TOOL_NAME --test --list`**: List available tests.
- **`TOOL_NAME --test --range 0 5`**: Run specific test range.

## Agent Mode

Every tool supports three interaction modes, mirroring AI IDE patterns:

| Flag | Mode | Capabilities |
|------|------|-------------|
| `--agent` | Agent | Full access: read, write, exec, edit |
| `--ask` | Ask | Read-only: read_file, search, read-only exec (ls, cat, grep, git log) |
| `--plan` | Plan | Read-only + no scripts: same as Ask but exec blocks script execution entirely |

```bash
# Agent mode — full capabilities
TOOL_NAME --agent prompt "Build a feature that..."
TOOL_NAME --agent feed <SESSION_ID> "Now add tests for it"

# Ask mode — read-only exploration
TOOL_NAME --ask prompt "How does the search function work?"

# Plan mode — read-only analysis and design
TOOL_NAME --plan prompt "Design an approach for adding caching"

# Shared subcommands
TOOL_NAME --agent status [SESSION_ID]
TOOL_NAME --agent sessions
TOOL_NAME --agent setup
```

### Session Management (`--session`)

`--session` is the unified session interface. `--agent`, `--ask`, `--plan` are shortcuts:

```bash
# Equivalent pairs:
TOOL_NAME --session agent prompt "..."    ≡  TOOL_NAME --agent prompt "..."
TOOL_NAME --session ask prompt "..."      ≡  TOOL_NAME --ask prompt "..."
TOOL_NAME --session plan prompt "..."     ≡  TOOL_NAME --plan prompt "..."

# Session checkout — switch active session or create new
TOOL_NAME --session checkout              # Create new session
TOOL_NAME --session checkout <SID>        # Switch to existing session

# Session cleanup — delete sessions
TOOL_NAME --session clean <SID1> [SID2 ...]  # Delete specific sessions
TOOL_NAME --session clean --all              # Delete ALL sessions

# Task queue — manage queued tasks (auto-queued when session is busy)
TOOL_NAME --session queue                    # List queued tasks
TOOL_NAME --session queue clear              # Clear the queue
```

Session data is stored in `runtime/sessions/<session_id>/history.json`. Response data from AI IDE agents is stored in `runtime/sessions/<session_id>/data/<response_id>.json` (sequential: `000.json`, `001.json`, ..., `999.json`, `1000.json`).

Agent infrastructure lives in `logic/agent/` (core) and `interface/agent.py` (facade). Each tool can extend agent behavior via `tool/<NAME>/logic/agent/`. Three assistance tiers: 0 (minimal, for AI IDEs), 1 (standard), 2 (full with nudges and quality checks).

Default LLM provider: `zhipu-glm-4.7` (GLM-4.7 via Zhipu AI). Configure via `--agent setup`.

### Self-Operate Mode

Self-operate mode allows an AI IDE (e.g., Cursor) to use the assistant GUI as its own interface, driving the conversation from the terminal rather than through a remote LLM provider.

```bash
# Start self-operate session with prompt
TOOL_NAME --agent --self-operate --self-name "Opus 4.6" --env "IDE/cursor" prompt "Create a hello.py"

# Inject a response (simulates an LLM API reply)
TOOL_NAME --agent response <SESSION_ID> '<json_events>'

# Complete the task
TOOL_NAME --agent response <SESSION_ID> '[{"type":"complete","reason":"done"}]'
```

**Options:**
- `--self-operate`: Enables self-operate mode. The prompt is displayed in the GUI but NOT sent to an LLM provider. The chatbox input is disabled until the task completes.
- `--self-name "Name"`: Display name for the operating agent (e.g., "Opus 4.6").
- `--env "IDE/cursor"`: Environment identifier. The last path segment is used to resolve a logo from `logic/asset/image/env/IDE/`. If not specified, a default bot icon is shown.

**Flow:**
1. `--self-operate prompt "..."` creates a new GUI session, shows the user prompt and a model banner with the env logo + name, and waits for `--response`.
2. `--response <SID> <json>` injects events (text, tool calls, etc.) into the session. Tool calls are executed server-side.
3. Repeat step 2 until the task is done, then inject a `complete` event.

**Environment logos** are stored in `logic/asset/image/env/IDE/` (cursor.svg, copilot.svg, windsurf.svg).

**Auto Model Selection**: Use provider name `auto` for automatic model selection with fallback. The Auto provider ranks available models by stability (free-tier preference, RPM headroom, error rate tracking) and automatically falls back to the next model on 429/500 errors. Implemented in `tool/LLM/logic/auto.py`.

### Exec Timeout & Background Execution

The agent's `exec` tool supports `block_until_ms` (default: 30000ms). When a command exceeds this timeout, it automatically moves to background execution:
- The agent receives the PID immediately (not blocked)
- The command continues running in the background
- Set `block_until_ms=0` to run immediately in background (for dev servers, watchers)
- Use `timeout_policy="error"` to report failure on timeout instead of ok

### Read-Only Sandbox

Ask and Plan modes enforce a read-only sandbox at **two levels**:

1. **Tool definitions** (`logic/agent/tools.py`): `write_file` and `edit_file` are removed from the tool list
2. **Runtime enforcement** (`conversation.py`): `_check_mode_restriction()` blocks write/edit tool calls and unsafe exec commands even if the LLM tries to call them

- `exec` only allows read-only commands; write/modify commands are blocked
- Plan mode additionally blocks all script execution (python3 script.py, etc.)
- The sandbox is enforced in `logic/agent/tools.py` via `_is_readonly_safe()` and `_is_plan_safe()`

Session IDs use the format `YYYYMMDD-HHMMSS-<6hex>` for chronological sorting.

### AI IDE Integration Workflow

**If you are an AI IDE agent** (e.g., Cursor, Copilot, Windsurf, or any IDE that provides built-in file/terminal tools), this project offers its own equivalent tools that integrate with the project's progress tracking, nudge system, and session management. Follow this workflow to leverage the project ecosystem instead of relying solely on the IDE's built-in tools.

**Why use project tools instead of IDE tools?** Our tools automatically track file modifications, trigger quality checks, emit UI events to the HTML GUI, and feed session context to the nudge/hint system. IDE tools bypass all of this.

**When to fallback to IDE tools:** If the project's equivalent tool has a bug that you cannot fix, or if the IDE provides a capability not yet developed in the project, continue using the IDE tool. Fix the project tool's bug first if possible.

#### Step-by-step workflow

**i. Detection**: If you discover you are running inside an AI IDE (you have access to IDE-provided read/write/exec tools), read this section. Otherwise, skip.

**ii. Tool substitution**: Use the AI IDE's `exec` tool to call our standard tool commands instead of using the IDE's built-in file operations directly:

```bash
# Instead of IDE read_file → use our exec:
exec("TOOL_NAME --ask --dry-run prompt 'read file X'")

# Instead of IDE write_file → use our response injection:
exec("TOOL_NAME --agent --response <session_id> <path.json>")
```

**iii. Starting a task**: When you receive user input `<prompt>`, first run:

```bash
TOOL_NAME --agent --dry-run prompt "<prompt>"
```

Choose `--ask`, `--plan`, or `--agent` based on the task type (`--debug` and other modes map to `--agent`). The `--dry-run` flag:
- Creates a new session in the GUI (opens the browser tab)
- Shows the system prompt, user message, and available tools
- Does NOT send to the remote LLM provider — YOU are the provider

**iv. Providing responses**: Write your response as JSON following the OpenAI response protocol, save it to `runtime/sessions/<session_id>/data/<response_id>.json`, then inject:

```bash
TOOL_NAME --agent --response <session_id> runtime/sessions/<session_id>/data/000.json
```

Response IDs are sequential: `000.json`, `001.json`, ..., `999.json`, `1000.json`.

The terminal will show no output on success. Warnings indicate protocol violations (e.g., invalid JSON, schema mismatch).

**v. Checking state**: At any time:

```bash
# View recent conversation events
TOOL_NAME --agent history <session_id> --limit 20

# View current session state (what a new agent would see if resuming)
TOOL_NAME --agent feed <session_id>
```

`--feed` provides the same ecosystem information as `--prompt` (system prompt, context, tools). It supports `--dry-run` to preview without executing.

**vi. Receiving tool results**: After you inject a response containing tool calls, the system executes them and returns results via the feed. Check `--history` or `--feed` to see tool execution results.

**vii. Task completion**: When your session task is complete, the system emits a `complete` event. Continue to the next step.

**viii. USERINPUT loop**: After completing all session tasks, call `USERINPUT` to get user feedback. If feedback arrives, return to step iii with the new prompt. If no feedback, perform related development/testing tasks and retry `USERINPUT`.

### USERINPUT Feedback Loop

`USERINPUT` is a **standalone terminal command** (not a `main.py` subcommand). Execute it directly:

```bash
# Direct execution (preferred):
./bin/USERINPUT/USERINPUT --hint "Task completed, awaiting feedback"

# With PATH configured (after setup.py):
USERINPUT --hint "Task completed"
```

**Important**: Do NOT redirect stderr (`2>&1`) when calling USERINPUT — it uses real-time terminal output for progress display. Never set `--timeout` below the default (300s). See the `userinput-feedback-loop` skill for details.

**IMPORTANT for skills discoverability**: If a user asks you to locate a skill and you cannot find it, you should create a new skill and adjust relevant README.md / for_agent.md files to improve discoverability for future agents.

### Brain Types & Memory

Agents accumulate experience via "brain types" — named collections of personality, memory, and user context stored in `experience/<brain_type>/`:

```
experience/default/
    SOUL.md        — Agent personality, communication style, values
    IDENTITY.md    — Agent name, role, goals
    USER.md        — User preferences
    MEMORY.md      — Long-term persistent facts
    daily/         — Daily working logs (YYYY-MM-DD.md)
```

Manage brains: `TOOL_NAME --agent brain [list|init <name>|show <name>]`

In Tier 2, bootstrap files are injected into the system prompt automatically. Memory tools (`write_memory`, `write_daily`, `recall_memory`) are available in agent mode for persistent knowledge.

Session export/import enables knowledge transfer: `--agent export <SID>` creates a portable `.tar.gz`, and `--agent import <archive> [brain_type]` restores it.

## 4. Progress Display Patterns

Run `SKILLS show turing-machine-development` for comprehensive guidance on the Turing Machine system.

### Quick Reference
- **Sequential stages**: `ProgressTuringMachine` with `TuringStage` objects.
- **Parallel tasks**: `ParallelWorkerPool` with N-worker concurrency.
- **Ephemeral mode**: `pm.run(ephemeral=True)` erases progress lines after completion.
- **Stealth mode**: `TuringStage(stealth=True)` for silent background operations.

## 5. GUI Development
Inherit from blueprints in `logic/gui/tkinter/blueprint/`:
- **`timed_bottom_bar`**: Base blueprint with timeout and standard buttons.
- **`account_login`**: Account/Password login.
- **`two_factor_auth`**: N-digit verification.
- **`tutorial`**: Multi-step setup wizards. Run `SKILLS show setup-tutorial-creation` for details.

Key patterns:
- Use `logic.gui.engine.get_safe_python_for_gui()` for sandboxed environments.
- Use `logic.gui.manager.run_gui_subprocess()` for external tool GUIs.

## 6. Localization (i18n)
- **Strings**: Never hardcode user-facing strings. Use the `_()` helper.
- **English First**: Do NOT include an `en.json`. English strings must be provided as the default argument in the code: `_("key", "Default English Text")`.
- **Translation Files**: Place translations in `logic/translation/<lang>.json`.

## 7. Critical Directives
As an AI agent, you MUST follow these operational rules:
- **Command Entry**: Always prefer using absolute paths for tool call arguments. All installed tools are standalone terminal commands — call them directly by name (e.g., `USERINPUT`, `GIT`, `PYTHON`, `LLM`). Their executables live in `bin/<NAME>/<NAME>` and are auto-added to `PATH` by `setup.py`. This is the universal mechanism for the entire project.
- **Feedback Acquisition**: After completing any task, you **MUST** execute `USERINPUT` directly in the terminal (it is a standalone command, not a subcommand of `main.py`). Example: `USERINPUT --hint "Task done"`. Do not redirect stderr. This is a mandatory safety and synchronization check.
- **Safety**: Never commit code with syntax errors. Always use `read_lints` before finishing.
- **Avoid Background Tests**: Never execute `TOOL test PYTHON` (or other core tests) in the background. Background execution of complex test suites can cause agent calling loops and system instability. Always ask the user to run tests if needed.
- **Branch Management**: `TOOL test` automatically records your current branch and restores it after tests finish, even if tests fail. This prevents you from accidentally remaining on the `test` branch after a failure. ALWAYS verify your current branch with `git branch` before committing, especially after running sync or test commands.
- **Binary Files**: If you must track binary files (like in `tool/PYTHON/data/install/`), ensure they are marked as `binary` in `.gitattributes` to prevent corruption by line-ending conversion.
- **Shadowing**: When developing tools, use the Universal Path Resolver (`from interface.resolve import setup_paths; setup_paths(__file__)`) to ensure the project root is at `sys.path[0]`. This prevents a tool's local `logic/` from shadowing the root `logic/`.
- **Import facade**: All code outside `logic/` and `interface/` MUST import from `interface.*`, never from `logic.*` directly. This includes `main.py`, `setup.py`, hooks, and tests. Only code inside `logic/` may call other `logic/` modules. Run `TOOL --audit imports` to check compliance. See the `code-quality-review` skill for the full rule set (IMP001-IMP005).
- **`.gitignore` is auto-generated**: Never edit `.gitignore` directly. Modify `GitIgnoreManager.base_patterns` in `logic/git/manager.py` instead. See Section 9.
- **TM hygiene**: Never use `print()` inside a `TuringStage` action. Use `stage.refresh()` if you need live updates, or rely on the stage success/fail messages. Inner prints break the erasable line tracking.
- **Keyboard Cancellation**: When a user cancels an operation (Ctrl+C or USERINPUT Cancel button), the system prints a red bold "**Operation cancelled** by user." message, ensures keyboard suppression is released, and exits with code 130 (POSIX SIGINT convention). USERINPUT's Cancel button produces the same exit code 130, so the Turing Machine's `INTERRUPTED` state handles both uniformly.
- **Reference Counting**: The `KeyboardSuppressor` uses reference counting to prevent deadlocks and ensure input echoing is restored only after all active suppressors have stopped.
- **Exit Codes**: If your tool is a proxy or re-executes another command, always use `sys.exit(process.returncode)` to propagate the exit status.
- **Sanity Checks**: Every tool MUST pass `TOOL --dev sanity-check <NAME>` (or `TOOL_NAME --dev sanity-check`). This ensures basic files like `README.md`, `setup.py`, and `test/test_00_help.py` exist.

## 8. Universal Path Resolver Protocol
The `logic.resolve` module provides a canonical way to find the project root and configure `sys.path` for correct cross-tool imports. This replaces the duplicated `find_project_root()` functions that previously existed in every tool.

### Usage
**In tool main.py / setup.py** (bootstrap preamble):
```python
import sys; from pathlib import Path
_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)
```

**In modules already managed by ToolBase** (sys.path is already set):
```python
from interface.resolve import setup_paths
ROOT = setup_paths(__file__)
```

The resolver ensures the project root is at `sys.path[0]` and removes conflicting entries (like a tool's own directory). This prevents the `logic/tool/` package from shadowing the top-level `tool/` package.

### Cross-Tool Imports
Cross-tool imports use the interface layer:
```python
from interface.chrome import CDPSession, CDP_PORT
from tool.GOOGLE.interface.main import inject_and_execute
```

Tools with dots in their name (e.g., `GOOGLE.GDS`, `GOOGLE.GD`) cannot be imported as Python packages. Use their `interface/main.py` for the public API, or import from the parent tool's modules.

## 9. Key Shared Suites

### `interface/` — Facade Layer (IMPORT FROM HERE)
Tools import shared framework utilities from `interface.*`. See `interface/for_agent.md` for the full module map. Key modules:
- `interface.status`: Terminal formatters — `fmt_status()`, `fmt_warning()`, `fmt_info()`, `fmt_detail()`, `fmt_stage()`.
- `interface.utils`: Preflight checks, retry, cleanup, fuzzy suggestions, logging, timezone, system paths.
- `interface.config`: Colors, settings, global config.
- `interface.tool`: `ToolBase`, `MCPToolBase`, `ToolEngine`.
- `interface.turing`: `ProgressTuringMachine`, `TuringStage`, `ParallelWorkerPool`.
- `interface.audit`: `run_full_audit()`, `print_report()`.
- `interface.registry`: Dynamic tool interface loader — `get_tool_interface("TOOL_NAME")`.

### `logic/` — Internal Implementation (DO NOT import from tools)
- `logic.resolve`: Universal path resolver protocol (see above).
- `logic.config`: Centralized configuration, color management, and rule generation (`config.rule`).
- `logic.tool`: Tool lifecycle (`base`, `setup/`), dev commands (`tool.dev`), and audit caching (`tool.audit`).
- `logic.turing`: State machine progress display (`models/`), multi-line terminal management (`display/`), and keyboard suppression (`terminal/`).
- `logic.utils`: Split into submodules — `display` (formatting/tables), `system` (paths/platform), `progress` (ETA/retry), `cleanup`, `logging` (SessionLogger), `timezone`. All re-exported from `logic.utils` for backward compat.
- `logic.gui`: Tkinter blueprint framework for GUIs.
- `logic.accessibility.keyboard`: Global keyboard monitoring (`monitor`) and shortcut settings (`settings`).
- `logic.lang`: Language management, translation utilities, and audit.
- `logic.git`: Git operations, `.gitignore` auto-generation, persistence manager, and branch utilities. **See "Auto-Generated .gitignore" below.**
- `logic.chrome`: **Shared Chrome CDP infrastructure** — generic session management, tab finding, JS evaluation, input dispatch, screenshot capture, DOM helpers, and `fetch_api()`. Service-agnostic; used by GOOGLE, CLOUDFLARE, ASANA, ATLASSIAN, INTERCOM, KLING, LINEAR, and future CDP-based tools.
- `logic.cdp`: Backward-compatibility shims for Chrome CDP imports (redirects to `tool.GOOGLE.logic.chrome.*`).
- `logic.audit`: Code quality auditing infrastructure (ruff, vulture integration).

### Auto-Generated `.gitignore` (CRITICAL)
The `.gitignore` file is **auto-generated** by `GitIgnoreManager` in `logic/git/manager.py`. **Never edit `.gitignore` directly** — your changes will be overwritten on the next `TOOL --dev sync` or `initialize_git_state()` call.

To add a new root directory to Git tracking:
1. Add `"!/your_dir/"` to `GitIgnoreManager.base_patterns` in `logic/git/manager.py`.
2. Run `TOOL --dev sync` to regenerate `.gitignore`.

To add tool-specific ignore rules:
1. Add `"git_ignore": ["pattern1", "pattern2"]` to the tool's `tool.json`.
2. `GitIgnoreManager.get_tool_rules()` reads these and generates tool-specific sections.

The base patterns use `/*` (ignore everything) then `!/dir/` (un-ignore specific directories). Currently tracked: `logic/`, `interface/`, `bin/`, `test/`, `tool/`, `report/`, `skills/`, `research/`, `runtime/`.

### Unified Logging (`tool.log()`)
Every `ToolBase` instance provides a `log(message, extra=None, include_stack=True)` method for runtime logging. One log file per session is created in `data/log/` (e.g., `log_20260227_163000_12345.log`). The `handle_exception()` method automatically writes full tracebacks to the same session log. Log files are capped at 64 per tool, auto-cleaning oldest half when exceeded.

```python
tool = ToolBase("MY_TOOL")
tool.log("Auth started", extra="apple_id=user@example.com")
tool.log("Scan complete", extra="found=99400 photos")
# On exception:
tool.handle_exception(e)  # Writes traceback to session log
# Direct access:
logger = tool.get_session_logger()
print(f"Log at: {logger.path}")
```

## 10. Specialized Tools

### iCloudPD Tool
Parallel iCloud photo/video downloader with timezone management, stall detection, auto-retry, and local library integration. Operates as a subtool under the `iCloud` ecosystem.

### Google Ecosystem Tool Hierarchy
The GOOGLE tool family follows a layered architecture:

| Layer | Tool | Purpose |
|-------|------|---------|
| Infrastructure | **GOOGLE** | Chrome CDP session, input dispatch, OAuth automation, screenshots |
| Data | **GOOGLE.GD** | Google Drive CRUD (create, delete, list files via gapi.client) |
| Compute | **GOOGLE.GC** | Google Colab cell injection, execution, tab management |
| Application | **GOOGLE.GDS** | Simulated shell on Colab (highest abstraction) |

**Import hierarchy**: GDS → GC + GD → GOOGLE. Generic Chrome CDP logic lives in `logic/chrome/session.py` (shared module). Google-specific logic lives in `tool/GOOGLE/logic/chrome/` with four modules:
- `session.py`: Re-exports from shared `logic.chrome.session` (backward compat)
- `colab.py`: Colab-specific cell injection and execution
- `drive.py`: Drive file operations via gapi.client
- `oauth.py`: Google OAuth consent flow automation

### GDS Tool
Google Drive Remote Controller for Colab:
- **Commands**: `GDS <command>` executes remotely. `GDS --raw <command>` executes with real-time output AND result capture. `GDS --no-capture <command>` runs without capturing output (for pip install, long tasks). `GDS ls`, `GDS cd`, `GDS pwd`, `GDS upload` for file management. `--setup-tutorial`, `--remount`, `--shell` for special operations.
- **File Operations**: `GDS read <file> [start] [end]` (line-numbered), `GDS grep <pattern> <file>` (regex search), `GDS linter <file>` (local lint via pyflakes/shellcheck), `GDS edit <file> <json_spec>` (remote text replacement).
- **Virtual Environments**: `GDS venv --create|--delete|--activate|--deactivate|--list|--current|--protect|--unprotect`. Active venvs inject `PYTHONPATH` into all remote commands automatically.
- **Background Execution**: `GDS bg <command>` runs long commands (pip install, git clone) in background. Track with `--status`, `--log`, `--result`, `--cleanup`.
- **Path Expansion**: `~` (remote root), `@` (remote env). Unquoted symbols expand; quoted symbols preserved. Handled by `utils.expand_remote_paths()`.
- **Upload**: Size-tiered strategies (base64 < 1MB, Drive Desktop sync 1-10MB, GUI drag-and-drop > 10MB).
- **Architecture**: Modular `logic/command/` structure. Non-interactive API via isolated tmp scripts. GUI serialization via `GUIQueue` (fcntl locking).
- **Exit Codes**: Bash-compatible non-zero on failure.

### Chrome CDP-Based Service Tools (CDMCP)
The following tools use `GOOGLE.CDMCP` to manage sessions and interact with web services through Chrome's DevTools Protocol. Each tool extends `MCPToolBase`, uses `boot_tool_session()` for session management, and `session.require_tab()` to find or open its service tab.

**Architecture**: All CDMCP tools follow the pattern: `MCPToolBase` → `cdmcp_loader` → `GOOGLE.CDMCP` session manager → `CDPSession` → web app DOM/API. Read `SKILLS show mcp-development` for the full development guide.

**Dependency**: Every CDMCP tool MUST declare `"GOOGLE.CDMCP"` in its `tool.json` `"dependencies"` array alongside `"PYTHON"`.

**Prerequisite**: Chrome must be running with `--remote-debugging-port=9222 --remote-allow-origins=*`. Run `CDMCP boot` to ensure a session is available.

#### CLOUDFLARE
Cloudflare account management via `dash.cloudflare.com/api/v4/`:
- `CLOUDFLARE user` — authenticated user info
- `CLOUDFLARE account` — account name, ID, type
- `CLOUDFLARE zones` — list DNS zones
- `CLOUDFLARE dns <zone_id>` — list DNS records
- `CLOUDFLARE workers` — list Workers scripts
- `CLOUDFLARE pages` — list Pages projects
- `CLOUDFLARE kv` — list KV namespaces

#### ASANA
Asana project management via `app.asana.com/api/1.0/`:
- `ASANA me` — user info and workspaces
- `ASANA workspaces` — list workspaces
- `ASANA projects <ws_gid>` — list projects
- `ASANA tasks <ws_gid>` — list assigned tasks
- `ASANA create-task <ws_gid> <name>` — create task
- `ASANA create-project <ws_gid> <name>` — create project
- `ASANA search <ws_gid> <query>` — search tasks
- `ASANA complete <task_gid>` — mark task done

#### ATLASSIAN
Atlassian account management via `home.atlassian.com/gateway/api/`:
- `ATLASSIAN me` — user profile
- `ATLASSIAN notifications` — recent notifications
- `ATLASSIAN preferences` — locale, timezone, account info

#### INTERCOM
Intercom customer messaging via `app.intercom.com` CDP session:
- `INTERCOM status` — authentication state (sign-up vs authenticated)
- `INTERCOM page` — current page title, URL, heading
- `INTERCOM conversations` — list recent conversations (requires auth)
- `INTERCOM contacts` — list contacts (requires auth)

#### KLING
Kling AI video generation via `app.klingai.com` CDP session. Data is read from localStorage and DOM since the API gateway (`api-app-global.klingai.com`) blocks cross-origin fetch:
- `KLING me` — user info (ID, name, email from localStorage)
- `KLING points` — credit points balance (from DOM)
- `KLING page` — current page state
- `KLING history` — generation history (from Assets page DOM)

#### LINEAR
Linear product development via `linear.app` CDP session. Data is read from localStorage (`ApplicationStore`) since the GraphQL API requires token auth:
- `LINEAR status` — authentication and organization state
- `LINEAR me` — user info (account ID, email, organizations)

#### PAYPAL
PayPal payment integration via `paypal.com` CDP session. Data is read from the dashboard DOM when authenticated:
- `PAYPAL status` — authentication state (login page vs dashboard)
- `PAYPAL page` — current page title, URL, heading
- `PAYPAL account` — account info: name, email, balance (requires auth)
- `PAYPAL activity` — recent transactions from dashboard (requires auth)

#### SENTRY
Sentry error monitoring via `sentry.io` CDP session. Uses same-origin REST API (`/api/0/`) with session cookies:
- `SENTRY status` — authentication state
- `SENTRY page` — current page info
- `SENTRY orgs` — list organizations (requires auth)
- `SENTRY projects <org>` — list projects (requires auth)
- `SENTRY issues <org> [--project <slug>]` — list issues (requires auth)

#### SQUARE
Square business platform via `squareup.com` CDP session. Dashboard data is read from DOM when authenticated:
- `SQUARE status` — authentication state (login page vs dashboard)
- `SQUARE page` — current page title, URL, heading
- `SQUARE dashboard` — merchant name, balance, summary (requires auth)

#### WHATSAPP
WhatsApp Web messaging via `web.whatsapp.com` CDP session. Requires QR code linking with phone:
- `WHATSAPP status` — link/authentication state (QR scan needed vs linked)
- `WHATSAPP page` — current page info
- `WHATSAPP chats` — list visible chats: name, last message, time, unread count (requires link)
- `WHATSAPP profile` — push name and avatar status (requires link)

#### WPS
WPS Office / KDocs via `kdocs.cn` / `wps.com` CDP session. Supports WeChat/QQ/email login:
- `WPS status` — authentication state (login page vs docs page)
- `WPS page` — current page info
- `WPS me` — user info: name, avatar, localStorage data (requires auth)
- `WPS docs` — list recent documents from DOM (requires auth)

#### GMAIL
Gmail email client via `mail.google.com` CDP session. Data is read from the Gmail SPA DOM:
- `GMAIL status` — authentication state, email address, unread count (from title)
- `GMAIL page` — current page info and section (inbox, sent, etc.)
- `GMAIL inbox [--limit N]` — list inbox emails: from, subject, date, unread/starred (requires auth)
- `GMAIL labels` — list sidebar labels with counts (requires auth)
- `GMAIL search <query> [--limit N]` — search emails via hash navigation (requires auth)

### TAVILY Tool
AI-optimized web search:
- `TAVILY <query>`: Search with Turing Machine progress display.
- `TAVILY config --api-key <key>`: Store API key.
- `TAVILY --setup-tutorial`: Guided API key configuration.
- Options: `--depth basic|advanced`, `--max-results N`, `--include-answer`, `--raw`.

### MCP-Based Tools
The following tools wrap external MCP (Model Context Protocol) servers, providing unified CLI access to popular services. Each supports `<NAME> --mcp-status`, `<NAME> config <key> <value>`, and `<NAME> --setup`.

> **MCP Command Convention**: All MCP (browser automation) commands use the `--mcp-` prefix. For example: `FIGMA --mcp-boot`, `YOUTUBE --mcp-play`, `BILIBILI --mcp-search "query"`. Built-in tool commands (`--setup`, `--test`, `--dev`, `--rule`) do NOT use the `--mcp-` prefix.

> **Developing a new MCP tool?** Read the `cdmcp-web-exploration` skill first (`SKILLS show cdmcp-web-exploration`). It covers the full 6-phase development cycle: DOM discovery, pixel exploration, interaction testing, implementation, verification, and self-designed task validation.

**AI/Creative**:
- `MIDJOURNEY`: AI image generation/transformation via Midjourney (AceDataCloud).
- `HEYGEN`: AI avatar video generation via HeyGen API.
- `SUNO`: AI music generation, lyrics, covers via Suno API.
- `KIMI`: Kimi AI assistant for long-context understanding (Moonshot).

**Productivity/Collaboration**:
- `XMIND`: Mind mapping and brainstorming.
- `CHARTCUBE`: AntV ChartCube chart generation (30+ chart types, 4-step wizard, no auth required).

**Messaging/Communication**:
- `DINGTALK`: DingTalk messaging and workspace integration.

**Payments/Finance**:
- `STRIPE`: Payment processing via Stripe MCP.
- `PLAID`: Financial data and bank account integration.

**DevOps/Infrastructure**:
- `GITHUB`: GitHub repositories, issues, PRs (depends on GIT).
- `GITLAB`: GitLab repositories, merge requests, CI/CD.

**Automation**:
- `ZAPIER`: Workflow automation across 8000+ apps.

## 11. Testing Conventions
- **Naming**: `test_xx_name.py` (two-digit ID). Every tool must have `test_00_help.py`.
- **Execution**: `TOOL test <NAME>` runs all tests with CPU monitoring and branch management.
- **Per-test config**: `EXPECTED_TIMEOUT = 300` and `EXPECTED_CPU_LIMIT = 40.0` at file top.
- **Temporary Scripts**: Use `tmp/` for one-off verification. Run `SKILLS show tmp-test-script` for patterns.

## 12. Status Prompt Design
Run `SKILLS show turing-machine-development` for comprehensive Turing Machine guidance.

Key rules:
- **Colors**: Green (success), Blue (progress), Red (error), Yellow (warning). Bold status labels only.
- **Grammar**: Verb + Noun ("Syncing branches") or Adverb + Verb ("Successfully received").
- **Punctuation**: In-progress ends with `...`, completed ends with `.`.
- **Stealth**: `TuringStage(stealth=True)` for silent operations.

## 13. Skills System

Skills are structured best-practice guides that AI agents can reference during development.

### Skill Locations
- **Project-level** (`skills/core/`): Core framework skills. (`skills/AI-IDE/Cursor/`): Cursor-specific skills.
- **Library** (`tool/SKILLS/logic/library/`): 100 general CS skills (frontend, backend, DevOps, AI/ML, security, etc.). These are NOT synced to Cursor to avoid excessive context; use `SKILLS show <name>` to read them.
- **Tool-level** (`tool/<NAME>/skills/`): Per-tool skills for specialized patterns.

### Accessing Skills
- `<TOOLNAME> skills` — List skills relevant to a specific tool (from its `tool.json` `"skills"` field).
- `<TOOLNAME> skills show <name>` — Display a skill's full content.
- `<TOOLNAME> skills search <query>` — Search all skills by keyword.
- `SKILLS list` — List all available skills with link status.
- `SKILLS show <name>` — Display any skill by name.

### Marketplace
Browse, search, and install skills from external sources (ClawHub / OpenClaw ecosystem, 3000+ community skills):
- `SKILLS market browse` — Browse top downloaded skills.
- `SKILLS market search <query>` — Search the marketplace.
- `SKILLS market install <slug>` — Download and install a skill to `skills/marketplace/<source>/`.
- `SKILLS market uninstall <slug>` — Remove an installed marketplace skill.
- `SKILLS market sources` — List registered skill sources.
- `SKILLS market installed` — List installed marketplace skills.

### Evolution System
Agent self-improvement loop (inspired by OpenClaw). Brain data in `runtime/experience/`:
- `SKILLS learn "<lesson>" --tool NAME --severity info|warning|critical` — Record a lesson.
- `SKILLS lessons` — View recent lessons.
- `SKILLS analyze` — Pattern recognition across lessons.
- `SKILLS suggest` — Generate typed improvement suggestions.
- `SKILLS apply <id>` — Apply a suggestion with action guide.
- `SKILLS history` — View evolution audit trail.

### Key TerminalTools Skills
- `skills-index`: Master index of all framework skills.
- `tool-development-workflow`: Creating and deploying tools.
- `turing-machine-development`: Progress display system.
- `tool-interface`: Cross-tool `interface/` communication pattern.
- `setup-tutorial-creation`: Interactive setup wizards.
- `development-report`: Naming and content structure for `tool/<NAME>/data/report/` reports.
- `openclaw`: Self-improvement loop with lesson capture and enforcement hooks.
- `development-report`: Writing detailed reports in `data/report/`.
- `avoid-duplicate-implementations`: Detecting and eliminating duplicate code.
- `standard-command-development`: Interface-oriented three-layer architecture for all command types (CLI, MCP, future). Turing Machine integration and command composition patterns.

## 14. CDMCP Tool Development Best Practices

For full guidance, read `SKILLS show mcp-development` and `SKILLS show cdmcp-web-exploration`.

### Setup Checklist
1. Create tool: `TOOL --dev create <NAME>`
2. **tool.json**: Add `"PYTHON"` and `"GOOGLE.CDMCP"` to `"dependencies"`. Add `"websocket-client"` to `"pip_dependencies"`.
3. **Root tool.json**: Add the tool name to the `"tools"` array.
4. **main.py**: Use `MCPToolBase("NAME", session_name="name")` from `logic.tool.blueprint.mcp`.
5. **logic/chrome/api.py**: All CDP operations. Use `boot_tool_session()` + `session.require_tab()` + `CDPSession(ws)`.
6. **setup.py**: Verify `_r` (not `project_root`) in the path resolver.
7. Install: Run `<NAME> setup`.

### Session Boot Pattern
```python
from interface.cdmcp import load_cdmcp_sessions
from interface.chrome import CDPSession
sm = load_cdmcp_sessions()
boot_result = sm.boot_tool_session(session_name, timeout_sec=86400, port=9222)
session = boot_result["session"]
tab_info = session.require_tab(label, url_pattern=pattern, open_url=url,
                                auto_open=True, wait_sec=10)
cdp = CDPSession(tab_info["ws"])
```

### Unified `--mcp-state` Command

All `MCPToolBase` tools support `TOOL --mcp-state` for unified state inspection. Override `_collect_mcp_state()` to add tool-specific state.

### Known Pitfalls
- **WebSocket exclusivity**: Chrome allows ONE page-level WebSocket per target. Cache `CDPSession` per-process and `.close()` old connections before creating new ones.
- **SPA routing**: React/Vue SPAs return 404 on direct URL navigation. Navigate to the app root first, then use programmatic clicks to reach inner pages.
- **Session reuse**: Use `boot_tool_session()` (not manual `create_session` + `boot`). The function handles session reuse across tools sharing the same Chrome window.
- **Tab registration**: Always use `session.require_tab()` instead of raw `Target.createTarget`. Raw creation bypasses session tracking, causing orphan tabs and state corruption.
- **`@requires_cdp` gate**: All 15 Chrome-dependent CDMCP API functions use `@requires_cdp()` which automatically checks (1) Chrome installed, (2) CDP port reachable, (3) session window alive — with auto-recovery at each stage. Tool developers never call prerequisite checks manually. Use `@requires_cdp(check_session=False)` for functions that only need Chrome/CDP.
- **setup.py template**: `TOOL --dev create` template may reference `project_root` (undefined). Use `_r` instead.
- **Chrome CDP unavailable**: Add retry logic for `boot_tool_session` failures. Include an actionable hint in error messages (e.g., "run CDMCP boot first").
- **Disabled buttons**: Check `button.disabled` via CDP before assuming a click failed. Ant Design forms disable buttons until required fields are filled.
- **Duplicate implementations**: Before writing new code, search the codebase for existing implementations. See skill: `avoid-duplicate-implementations`.

## 15. Agent Bootstrap: Becoming an Effective Agent

This section distills the key mechanisms that every AI agent operating in this project should internalize. Whether you're an OpenClaw agent, a Cursor IDE agent, or any other AI assistant, these principles make you effective.

### Discovery Before Implementation
NEVER write new code before searching for existing tools, interfaces, and skills:

```
# Search for tools by capability
TOOL --search tools "send email"
TOOL --search interfaces "rate limiting"
SKILLS search "error recovery"

# Learn a specific tool
cat tool/TOOLNAME/for_agent.md
cat tool/TOOLNAME/README.md
```

Every tool has a `for_agent.md` with architecture details and a `README.md` with usage docs. Read them first.

### The Evolution Cycle
Your intelligence grows through a cycle. Each stage feeds the next:

```
Errors / Surprises
      ↓
  Lessons (atomic observations in runtime/experience/lessons.jsonl)
      ↓   (multiple lessons on the same theme)
  Skills (structured guides in skills/core/)
      ↓   (skills + repeated use cases)
  Infrastructure (utility functions in interface.*)
      ↓   (infra + real-world refinement)
  Better Infrastructure
```

- **Record lessons**: Use `SKILLS learn "description" --tool NAME --severity warning` after non-trivial fixes.
- **Review lessons**: `SKILLS lessons --last 20` before starting related work.
- **Audit skills**: Periodically check if skills can be converted to infrastructure (`interface.*` utilities or new tools). See `.cursor/rules/skills-to-infrastructure.mdc`.

### Tool Resilience
When a tool has a bug, **fix it** — do not work around it:
1. Read the tool's source code.
2. Identify the broken logic.
3. Fix the bug directly in the codebase.
4. Record the fix as a lesson.

When no tool exists for a needed capability:
1. Search thoroughly (tools, interfaces, skills).
2. Assess necessity: is this recurring/complex enough to justify a tool?
3. Prefer the simplest solution that works (shell one-liner > script > tool).
4. If building a tool: read `SKILLS show tool-development-workflow` first.

### Error Recovery Protocol
1. Read the error message carefully.
2. Search past lessons for similar issues.
3. Check `for_agent.md` and README of involved tools.
4. Try a fix. If it fails, try a different approach.
5. Record what you learned.

### Discoverability Mandate (CRITICAL)
Whenever you create or modify a skill, tool, infrastructure function, or unit test, **always consider whether a context-free agent can discover it**. If the answer is no, immediately:

1. Update the nearest `for_agent.md` and `README.md` to reference the new work.
2. Trace the documentation hierarchy upward — if a tool-level doc change is needed, also check whether `logic/for_agent.md` or even the root `for_agent.md` needs a mention.
3. For new skills: ensure `skills/core/skills-index/SKILL.md` includes it.
4. For new infrastructure: ensure `interface/for_agent.md` lists the new module.
5. For new tools: ensure `for_agent.md` Section 10 references the tool.

The test: imagine an agent that has never seen this project before and only reads `for_agent.md`. Can it find your work? If not, add breadcrumbs.

### Test Maturation
As tools mature, their features MUST be stabilized into unit tests. Read `SKILLS show unit-test-conventions` for the full guide. Key principle: every non-trivial bug fix should include a regression test. Tests must be localization-aware (accept both English and translated strings).

### Key Operational Habits
- **USERINPUT feedback**: Execute `USERINPUT` after completing tasks to get user feedback.
- **Branch awareness**: Always verify your branch with `git branch` before committing. `TOOL test` and `TOOL --dev sync` change branches.
- **Absolute paths**: Use absolute paths for tool call arguments.
- **No emoji**: Do not use emoji in code or console outputs.
- **Localization**: Never hardcode user-facing strings; use `_("key", "Default")`.
- **Import from `interface.*`**: Never import directly from `logic.*` in tool code.
- **`.gitignore` is auto-generated**: Modify `GitIgnoreManager.base_patterns` in `logic/git/manager.py`, not `.gitignore` directly.
- **Sanity checks**: Every tool must pass `TOOL --dev sanity-check <NAME>`.

By following these architecture rules and agent patterns, you ensure that the project remains robust, maintainable, and "agent-friendly."

