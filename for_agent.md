# AITerminalTools: Guide for AI Agents

Welcome to the `AITerminalTools` ecosystem. This guide is designed to provide you with the essential context and technical framework needed to develop, maintain, and interact with tools in this project.

## 1. Core Philosophy: Symmetry & Automation
This project follows a **Symmetrical Design Pattern**. Shared core logic resides in the root `logic/` folder, while each tool (located in `tool/`) has its own `logic/` directory for tool-specific implementations.

- **Isolation**: Use the `PYTHON` tool dependency to run your tool in a standalone runtime.
- **Persistence**: Work is automatically committed and pushed every few commits via git hooks to protect progress.
- **Persistence Manager**: Use `GitPersistenceManager` (via `TOOL dev sync` or `TOOL test`) to preserve non-Git-tracked directories (like Python installations) across branch switches.
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
  ├── tool.json        # Metadata & dependencies (e.g., "dependencies": ["PYTHON"])
  ├── test/            # Tool-specific unit tests (test_xx_name.py)
  └── README.md        # Documentation
```

## 3. The Tool Blueprint (`ToolBase`)
All tools inherit from `logic.tool.base.ToolBase`. Key features:
- **`handle_command_line(parser)`**: Standardizes argument processing. Handles `setup`, `install`, `uninstall`, `rule`, `config`, `skills` commands automatically.
- **Help Support**: Every tool MUST support `-h` and `--help`.
- **Python Runtime**: If `PYTHON` is a dependency, ToolBase ensures the isolated Python environment is used.
- **System Fallback**: Unrecognized commands delegate to system equivalents (e.g., `GIT` → `/usr/bin/git`).
- **CPU Monitoring**: Automatic CPU load check with configurable threshold and warning.
- **Programmatic Interface**: `--tool-quiet` returns results as `TOOL_RESULT_JSON:...` for machine consumption.
- **Unified Success**: `self.raise_success_status("action")` for green-bold **Successfully [action]** messages.
- **Path Resolution**: Use `self.tool_dir`, `self.get_data_dir()`, `self.get_log_dir()`.

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

### Synchronization Commands
- **`TOOL dev sync`**: The primary command to synchronize all branches. Commits on `dev`, aligns `tool` (preserving `resource/` from old tool branch via force-add), strips `tool`/`resource` for `main`, and syncs `test`.
- **`TOOL dev align`**: An alias for `dev sync`.
- **`TOOL dev audit-test <NAME>`**: Audits unit test naming conventions for a tool or `root`. Ensures files follow `test_XX_name.py` and that `test_00` is reserved for the help test. Use `--fix` to automatically correct violations.
- **`TOOL dev audit-archived`**: Checks for duplicate tools between `tool/` and `resource/archived/`. No tool should exist in both locations.

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
- **Shadowing**: When developing tools with their own `logic/` directory, ALWAYS ensure the project root is at index 0 of `sys.path` before any imports that might find the tool's local `logic/` instead of the root `logic/`.
- **TM hygiene**: Never use `print()` inside a `TuringStage` action. Use `stage.refresh()` if you need live updates, or rely on the stage success/fail messages. Inner prints break the erasable line tracking.
- **Keyboard Cancellation**: When a user cancels an operation (Ctrl+C), the system prints a yellow bold "**Operation cancelled** by user." message and ensures keyboard suppression is correctly released.
- **Reference Counting**: The `KeyboardSuppressor` uses reference counting to prevent deadlocks and ensure input echoing is restored only after all active suppressors have stopped.
- **Exit Codes**: If your tool is a proxy or re-executes another command, always use `sys.exit(process.returncode)` to propagate the exit status.
- **Sanity Checks**: Every tool MUST pass `bin/TOOL dev sanity-check <NAME>`. This ensures basic files like `README.md`, `setup.py`, and `test/test_00_help.py` exist.

## 8. Key Shared Suites
- `logic.config`: Centralized configuration and color management.
- `logic.audit`: General-purpose audit logging and caching.
- `logic.utils`: Shared terminal utilities, path resolvers, RTL support, `SessionLogger`, and `@retry` decorator for API calls.

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

## 9. Specialized Tools

### iCloudPD Tool
Parallel iCloud photo/video downloader with timezone management, stall detection, auto-retry, and local library integration. Operates as a subtool under the `iCloud` ecosystem.

### GCS Tool
Google Drive Remote Controller for Colab:
- **Commands**: `GCS <command>` executes remotely. `GCS ls`, `GCS cd`, `GCS pwd`, `GCS upload` for file management. `--setup-tutorial`, `--remount`, `--shell` for special operations.
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

## 10. Testing Conventions
- **Naming**: `test_xx_name.py` (two-digit ID). Every tool must have `test_00_help.py`.
- **Execution**: `TOOL test <NAME>` runs all tests with CPU monitoring and branch management.
- **Per-test config**: `EXPECTED_TIMEOUT = 300` and `EXPECTED_CPU_LIMIT = 40.0` at file top.
- **Temporary Scripts**: Use `tmp/` for one-off verification. Run `SKILLS show TerminalTools-tmp-test-script` for patterns.

## 11. Status Prompt Design
Run `SKILLS show TerminalTools-turing-machine-development` for comprehensive Turing Machine guidance.

Key rules:
- **Colors**: Green (success), Blue (progress), Red (error), Yellow (warning). Bold status labels only.
- **Grammar**: Verb + Noun ("Syncing branches") or Adverb + Verb ("Successfully received").
- **Punctuation**: In-progress ends with `...`, completed ends with `.`.
- **Stealth**: `TuringStage(stealth=True)` for silent operations.

## 12. Skills System

Skills are structured best-practice guides that AI agents can reference during development.

### Skill Locations
- **Project-level** (`skills/`): `TerminalTools-*` skills for this framework's patterns.
- **Library** (`tool/SKILLS/data/library/`): 100 general CS skills (frontend, backend, DevOps, AI/ML, security, etc.).
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

