# AITerminalTools: Guide for AI Agents

Welcome to the `AITerminalTools` ecosystem. This guide is designed to provide you with the essential context and technical framework needed to develop, maintain, and interact with tools in this project.

## 1. Core Philosophy: Symmetry & Automation
This project follows a **Symmetrical Design Pattern**. Shared core logic resides in the root `logic/` folder, while each tool (located in `tool/`) has its own `logic/` directory for tool-specific implementations.

- **Isolation**: Use the `PYTHON` tool dependency to run your tool in a standalone runtime.
- **Persistence**: Work is automatically committed and pushed every few commits via git hooks to protect progress.

## 2. Standard Tool Structure
Every tool MUST be created using the command: `python3 main.py dev create <NAME>`. For sub-tools belonging to a specific ecosystem, use the flat namespace naming convention: `<PARENT_NAME>.<SUBTOOL_NAME>`.

### Tool Directory Layout
```text
tool/<NAME>/           # e.g., tool/iCloud/ or tool/iCloud.iCloudPD/
  ├── logic/           # Internal logic
  │   └── translation/ # Localization (zh.json, ar.json, etc.)
  ├── main.py          # Entry point (inherits from ToolBase)
  ├── setup.py         # Installation logic
  ├── tool.json        # Metadata & dependencies
  └── README.md        # Documentation
```

## 3. The Tool Blueprint (`ToolBase`)
All tools should inherit from `logic.tool.base.ToolBase`. This class provides:
- **`handle_command_line(parser)`**: Standardizes argument processing. It automatically handles `setup`, `install`, and `rule` commands.
- **Flat Namespace Support**: Sub-tools are identified by the dot notation (e.g., `GOOGLE.GCS`). The parent tool (e.g., `GOOGLE`) automatically delegates the `install` and `uninstall` commands to the correctly named flat sub-tool.
- **Robust Path Resolution**: Use `self.tool_dir`, `self.get_data_dir()`, and `self.get_log_dir()` to handle tool paths correctly.
- **Namespace Awareness**: `self.tool_module_path` provides the standard module path (e.g., `tool.iCloud_iCloudPD` or `tool.iCloud`).
- **System Fallback**: If a command is not recognized by the tool (e.g., `git status` called via the `GIT` tool), it automatically delegates the call to the system equivalent (e.g., `/usr/bin/git`).
- **Programmatic Interface**: Supports `--tool-quiet` to return results as JSON strings (`TOOL_RESULT_JSON:...`) for parent process consumption.
- **Unified Success Status**: Use `self.raise_success_status("action statement")` for standardized green-bold success messages.

## 4. Progress Display Patterns

### A. The Turing Machine (Sequential)
For multi-stage sequential operations, use `logic.turing.models.progress.ProgressTuringMachine`. It provides a "clean" terminal experience with erasable intermediate states.

### B. Parallel Worker Pool
For parallel tasks (e.g. downloads), use `logic.turing.models.worker.ParallelWorkerPool`. It supports N-worker concurrency and a dynamic one-line status bar.

#### Parallel Progress UI Style:
`Downloading yyyy-mm-dd/a, yyyy-mm-dd/b... (mmm/nnn)`

```python
from logic.turing.models.worker import ParallelWorkerPool

pool = ParallelWorkerPool(max_workers=3, status_label="Downloading")
pool.status_bar.set_counts(total_count)

# Tasks: [{"id": "yyyy-mm-dd/file", "action": func, "args": (...) }]
pool.run(tasks, success_callback=lambda id, res: pool.status_bar.increment_completed())
```

## 5. GUI Development
Inherit from GUI blueprints in `logic/gui/tkinter/blueprint/`:
- **`timed_bottom_bar`**: Base blueprint with timeout, countdown, and standard buttons.
- **`account_login`**: Specialized blueprint for Account/Password login (supports `account_initial` pre-fill).
- **`two_factor_auth`**: Specialized blueprint for N-digit square box verification.

- **Safe Execution**: Always use `logic.gui.engine.get_safe_python_for_gui()` to launch GUIs to ensure compatibility with sandboxed environments (like Cursor terminal).
- **Undo/Redo Support**: Use `logic.gui.tkinter.widget.text.UndoableText` for text input fields.

## 6. Localization (i18n)
- **Strings**: Never hardcode user-facing strings. Use the `_()` helper.
- **English First**: Do NOT include an `en.json`. English strings must be provided as the default argument in the code: `_("key", "Default English Text")`.
- **Translation Files**: Place translations in `logic/translation/<lang>.json`.

## 7. Critical Directives
As an AI agent, you MUST follow these operational rules:
- **Command Entry**: Always prefer using absolute paths for tool call arguments.
- **Feedback Acquisition**: After completing any task, you **MUST** execute the literal command `USERINPUT` in the terminal to obtain user feedback. This is a mandatory safety and synchronization check.
- **Safety**: Never commit code with syntax errors. Always use `read_lints` before finishing.

## 8. Key Shared Suites
- `logic.config`: Centralized configuration and color management.
- `logic.audit`: General-purpose audit logging and caching.
- `logic.utils`: Shared terminal utilities, path resolvers, and RTL support.

## 9. Testing Conventions
- **Unit Tests**: Place unit tests in the root `test/` directory.
- **Naming**: Follow the `test_xx_name.py` pattern, where `xx` is a two-digit ID (starting from `00`).
- **Temporary Scripts**: Use the root `tmp/` directory for one-off verification scripts or temporary test files.

By following this architecture, you ensure that the project remains robust, maintainable, and "agent-friendly." Good luck!

