# AITerminalTools: Guide for AI Agents

Welcome to the `AITerminalTools` ecosystem. This guide is designed to provide you with the essential context and technical framework needed to develop, maintain, and interact with tools in this project.

## 1. Core Philosophy: Symmetry & Automation
This project follows a **Symmetrical Design Pattern**. Shared core logic resides in the root `logic/` folder, while each tool (located in `tool/`) has its own `logic/` directory for tool-specific implementations.

- **Isolation**: Use the `PYTHON` tool dependency to run your tool in a standalone runtime.
- **Persistence**: Work is automatically committed and pushed every few commits via git hooks to protect progress.
- **Persistence Manager**: `GitPersistenceManager` automatically saves and restores non-Git-tracked directories across branch switches during `TOOL dev sync` and `TOOL test`. Tools declare which directories to preserve via `"persistence_dirs": ["data"]` in their `tool.json`. This is critical for API keys, session cookies, and configs that live in `data/` on the dev branch.
- **Managed Python Environment**: Use `PYTHON --enable` to create symlinks in `bin/` so that `which python` and `pip install` use the managed environment correctly.
- **Terminal Restoration**: The `KeyboardSuppressor` uses `atexit` to ensure terminal echoing is restored even if the process exits unexpectedly or via `KeyboardInterrupt`.

## 2. Standard Tool Structure
Every tool MUST be created using `TOOL dev create <NAME>`. Run `SKILLS show TerminalTools-tool-development-workflow` for the full development guide.

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
- **`handle_command_line(parser, dev_handler, test_handler)`**: Standardizes argument processing. Handles `setup`, `install`, `uninstall`, `rule`, `config`, `skills`, `--dev`, `--test` commands automatically. Custom `dev_handler` and `test_handler` callbacks can extend the built-in developer commands.
- **`--dev` Support**: Every tool supports `TOOL_NAME --dev <command>`. Built-in commands: `sanity-check [--fix]`, `audit-test [--fix]`, `info`. Tools can pass a custom `dev_handler` to `handle_command_line()` for tool-specific dev commands.
- **`--test` Support**: Every tool supports `TOOL_NAME --test [options]`. Runs the tool's unit tests with `--range`, `--max`, `--timeout`, `--list` options.
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

## 4. Progress Display Patterns

Run `SKILLS show TerminalTools-turing-machine-development` for comprehensive guidance on the Turing Machine system.

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
- **`tutorial`**: Multi-step setup wizards. Run `SKILLS show TerminalTools-setup-tutorial-creation` for details.

Key patterns:
- Use `logic.gui.engine.get_safe_python_for_gui()` for sandboxed environments.
- Use `logic.gui.manager.run_gui_subprocess()` for external tool GUIs.

## 6. Localization (i18n)
- **Strings**: Never hardcode user-facing strings. Use the `_()` helper.
- **English First**: Do NOT include an `en.json`. English strings must be provided as the default argument in the code: `_("key", "Default English Text")`.
- **Translation Files**: Place translations in `logic/translation/<lang>.json`.

## 7. Critical Directives
As an AI agent, you MUST follow these operational rules:
- **Command Entry**: Always prefer using absolute paths for tool call arguments.
- **Feedback Acquisition**: After completing any task, you **MUST** execute the literal command `USERINPUT` in the terminal to obtain user feedback. This is a mandatory safety and synchronization check.
- **Safety**: Never commit code with syntax errors. Always use `read_lints` before finishing.
- **Avoid Background Tests**: Never execute `TOOL test PYTHON` (or other core tests) in the background. Background execution of complex test suites can cause agent calling loops and system instability. Always ask the user to run tests if needed.
- **Branch Management**: `TOOL test` automatically records your current branch and restores it after tests finish, even if tests fail. This prevents you from accidentally remaining on the `test` branch after a failure. ALWAYS verify your current branch with `git branch` before committing, especially after running sync or test commands.
- **Binary Files**: If you must track binary files (like in `tool/PYTHON/data/install/`), ensure they are marked as `binary` in `.gitattributes` to prevent corruption by line-ending conversion.
- **Shadowing**: When developing tools, use the Universal Path Resolver (`from logic.resolve import setup_paths; setup_paths(__file__)`) to ensure the project root is at `sys.path[0]`. This prevents a tool's local `logic/` from shadowing the root `logic/`.
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
from logic.resolve import setup_paths
setup_paths(__file__)
```

**In modules already managed by ToolBase** (sys.path is already set):
```python
from logic.resolve import setup_paths
ROOT = setup_paths(__file__)
```

The resolver ensures the project root is at `sys.path[0]` and removes conflicting entries (like a tool's own directory). This prevents the `logic/tool/` package from shadowing the top-level `tool/` package.

### Cross-Tool Imports
Tools within the `tool/GOOGLE/` package can be imported directly:
```python
from tool.GOOGLE.logic.chrome.session import CDPSession, CDP_PORT
from tool.GOOGLE.logic.chrome.colab import inject_and_execute
```

Tools with dots in their name (e.g., `GOOGLE.GCS`, `GOOGLE.GD`) cannot be imported as Python packages. Use their `logic/interface/main.py` for the public API, or import from the parent tool's modules.

## 9. Key Shared Suites (`logic/` Directory)
- `logic.resolve`: Universal path resolver protocol (see above).
- `logic.config`: Centralized configuration, color management, and rule generation (`config.rule`).
- `logic.tool`: Tool lifecycle (`base`, `setup/`), dev commands (`tool.dev`), and audit caching (`tool.audit`).
- `logic.turing`: State machine progress display (`models/`), multi-line terminal management (`display/`), and keyboard suppression (`terminal/`).
- `logic.utils`: Split into submodules — `display` (formatting/tables), `system` (paths/platform), `progress` (ETA/retry), `cleanup`, `logging` (SessionLogger), `timezone`. All re-exported from `logic.utils` for backward compat.
- `logic.gui`: Tkinter blueprint framework for GUIs.
- `logic.accessibility.keyboard`: Global keyboard monitoring (`monitor`) and shortcut settings (`settings`).
- `logic.lang`: Language management, translation utilities, and audit.
- `logic.git`: Git operations, persistence manager, and branch utilities.
- `logic.interface`: Cross-tool interface registry. Use `get_interface("TOOL_NAME")` to load any tool's interface module.
- `logic.cdp`: Backward-compatibility shims for Chrome CDP imports (redirects to `tool.GOOGLE.logic.chrome.*`).

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
| Application | **GOOGLE.GCS** | Simulated shell on Colab (highest abstraction) |

**Import hierarchy**: GCS → GC + GD → GOOGLE. All Chrome CDP logic lives in `tool/GOOGLE/logic/chrome/` with four modules:
- `session.py`: Core CDP session, tab management, input dispatch
- `colab.py`: Colab-specific cell injection and execution
- `drive.py`: Drive file operations via gapi.client
- `oauth.py`: Google OAuth consent flow automation

### GCS Tool
Google Drive Remote Controller for Colab:
- **Commands**: `GCS <command>` executes remotely. `GCS --raw <command>` executes with real-time output AND result capture. `GCS --no-capture <command>` runs without capturing output (for pip install, long tasks). `GCS ls`, `GCS cd`, `GCS pwd`, `GCS upload` for file management. `--setup-tutorial`, `--remount`, `--shell` for special operations.
- **File Operations**: `GCS read <file> [start] [end]` (line-numbered), `GCS grep <pattern> <file>` (regex search), `GCS linter <file>` (local lint via pyflakes/shellcheck), `GCS edit <file> <json_spec>` (remote text replacement).
- **Virtual Environments**: `GCS venv --create|--delete|--activate|--deactivate|--list|--current|--protect|--unprotect`. Active venvs inject `PYTHONPATH` into all remote commands automatically.
- **Background Execution**: `GCS bg <command>` runs long commands (pip install, git clone) in background. Track with `--status`, `--log`, `--result`, `--cleanup`.
- **Path Expansion**: `~` (remote root), `@` (remote env). Unquoted symbols expand; quoted symbols preserved. Handled by `utils.expand_remote_paths()`.
- **Upload**: Size-tiered strategies (base64 < 1MB, Drive Desktop sync 1-10MB, GUI drag-and-drop > 10MB).
- **Architecture**: Modular `logic/command/` structure. Non-interactive API via isolated tmp scripts. GUI serialization via `GUIQueue` (fcntl locking).
- **Exit Codes**: Bash-compatible non-zero on failure.

### TAVILY Tool
AI-optimized web search:
- `TAVILY <query>`: Search with Turing Machine progress display.
- `TAVILY config --api-key <key>`: Store API key.
- `TAVILY --setup-tutorial`: Guided API key configuration.
- Options: `--depth basic|advanced`, `--max-results N`, `--include-answer`, `--raw`.

### MCP-Based Tools
The following tools wrap external MCP (Model Context Protocol) servers, providing unified CLI access to popular services. Each supports `<NAME> status`, `<NAME> config <key> <value>`, and `<NAME> setup`.

**AI/Creative**:
- `KLING`: AI video generation (text-to-video, image-to-video, lip-sync) via Kling API.
- `MIDJOURNEY`: AI image generation/transformation via Midjourney (AceDataCloud).
- `HEYGEN`: AI avatar video generation via HeyGen API.
- `SUNO`: AI music generation, lyrics, covers via Suno API.
- `KIMI`: Kimi AI assistant for long-context understanding (Moonshot).

**Productivity/Collaboration**:
- `XMIND`: Mind mapping and brainstorming.
- `WPS`: WPS Office document integration.
- `ATLASSIAN`: Jira issues and Confluence pages management.
- `ASANA`: Project and task management.
- `LINEAR`: Product development issue tracking.

**Messaging/Communication**:
- `DINGTALK`: DingTalk messaging and workspace integration.
- `WHATSAPP`: WhatsApp Business API messaging.
- `INTERCOM`: Customer messaging and support.

**Payments/Finance**:
- `STRIPE`: Payment processing via Stripe MCP.
- `PAYPAL`: PayPal payment integration.
- `SQUARE`: Business and payment platform.
- `PLAID`: Financial data and bank account integration.

**DevOps/Infrastructure**:
- `GITHUB`: GitHub repositories, issues, PRs (depends on GIT).
- `GITLAB`: GitLab repositories, merge requests, CI/CD.
- `SENTRY`: AI-powered error monitoring and debugging.
- `CLOUDFLARE`: DNS, Workers, R2 storage, analytics.

**Automation**:
- `ZAPIER`: Workflow automation across 8000+ apps.

## 11. Testing Conventions
- **Naming**: `test_xx_name.py` (two-digit ID). Every tool must have `test_00_help.py`.
- **Execution**: `TOOL test <NAME>` runs all tests with CPU monitoring and branch management.
- **Per-test config**: `EXPECTED_TIMEOUT = 300` and `EXPECTED_CPU_LIMIT = 40.0` at file top.
- **Temporary Scripts**: Use `tmp/` for one-off verification. Run `SKILLS show TerminalTools-tmp-test-script` for patterns.

## 12. Status Prompt Design
Run `SKILLS show TerminalTools-turing-machine-development` for comprehensive Turing Machine guidance.

Key rules:
- **Colors**: Green (success), Blue (progress), Red (error), Yellow (warning). Bold status labels only.
- **Grammar**: Verb + Noun ("Syncing branches") or Adverb + Verb ("Successfully received").
- **Punctuation**: In-progress ends with `...`, completed ends with `.`.
- **Stealth**: `TuringStage(stealth=True)` for silent operations.

## 13. Skills System

Skills are structured best-practice guides that AI agents can reference during development.

### Skill Locations
- **Project-level** (`skills/`): `TerminalTools-*` skills for this framework's patterns.
- **Library** (`tool/SKILLS/logic/library/`): 100 general CS skills (frontend, backend, DevOps, AI/ML, security, etc.). These are NOT synced to Cursor to avoid excessive context; use `SKILLS show <name>` to read them.
- **Tool-level** (`tool/<NAME>/skills/`): Per-tool skills for specialized patterns.

### Accessing Skills
- `<TOOLNAME> skills` — List skills relevant to a specific tool (from its `tool.json` `"skills"` field).
- `<TOOLNAME> skills show <name>` — Display a skill's full content.
- `<TOOLNAME> skills search <query>` — Search all skills by keyword.
- `SKILLS list` — List all available skills with link status.
- `SKILLS show <name>` — Display any skill by name.

### Key TerminalTools Skills
- `TerminalTools-skills-index`: Master index of all framework skills.
- `TerminalTools-tool-development-workflow`: Creating and deploying tools.
- `TerminalTools-turing-machine-development`: Progress display system.
- `TerminalTools-tool-interface`: Cross-tool `logic/interface` communication pattern.
- `TerminalTools-setup-tutorial-creation`: Interactive setup wizards.

By following these architecture rules, you ensure that the project remains robust, maintainable, and "agent-friendly."

