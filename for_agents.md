# AITerminalTools: Guide for AI Agents

Welcome to the `AITerminalTools` ecosystem. This guide is designed to provide you with the essential context and technical framework needed to develop, maintain, and interact with tools in this project.

## 1. Core Philosophy: Symmetry & Automation
This project follows a **Symmetrical Design Pattern**. Shared core logic resides in the root `logic/` folder, while each tool (located in `tool/`) has its own `logic/` directory for tool-specific implementations.

- **Isolation**: Use the `PYTHON` tool dependency to run your tool in a standalone runtime.
- **Persistence**: Work is automatically committed and pushed every few commits via git hooks to protect progress.

## 2. Standard Tool Structure
Every tool MUST be created using the command: `python3 main.py dev create <NAME>`. This generates the following structure:
```text
tool/<NAME>/
  ├── logic/                # Internal logic
  │   └── translation/      # Localization (zh.json, ar.json, etc.)
  ├── main.py               # Entry point (inherits from ToolBase)
  ├── setup.py              # Installation logic
  ├── tool.json             # Metadata & dependencies
  └── README.md             # Documentation
```

## 3. The Tool Blueprint (`ToolBase`)
All tools should inherit from `logic.tool.base.ToolBase`. This class provides:
- **`handle_command_line(parser)`**: Standardizes argument processing. It automatically handles `setup`, `install`, and `rule` commands.
- **System Fallback**: If a command is not recognized by the tool (e.g., `git status` called via the `GIT` tool), it automatically delegates the call to the system equivalent (e.g., `/usr/bin/git`).
- **Programmatic Interface**: Supports `--tool-quiet` to return results as JSON strings (`TOOL_RESULT_JSON:...`) for parent process consumption.

## 4. The Turing Machine Pattern (Progress Display)
For multi-stage operations, use `logic.turing.models.progress.ProgressTuringMachine`. It provides a "clean" terminal experience with erasable intermediate states.

### Usage Example:
```python
from logic.turing.logic import TuringStage
from logic.turing.models.progress import ProgressTuringMachine

def my_action():
    # ... logic ...
    return True

pm = ProgressTuringMachine([
    TuringStage("step1", my_action, 
                active_status="Processing", 
                success_status="Completed",
                fail_status="Warning", 
                fail_color="YELLOW")
], tool_name="MY_TOOL")

# ephemeral=True allows intermediate statuses to be overwritten/erased
pm.run(ephemeral=True, final_msg="") 
```

## 5. GUI Development
Inherit from `logic.gui.base.BaseGUIWindow` for a consistent Look & Feel.
- **Centralized Styling**: Use `logic.gui.style` for labels, buttons, and colors.
- **Bottom Bar**: Use `setup_common_bottom_bar` to add a status label, countdown timer, and standard buttons (Login/Submit, Add Time, Cancel).
- **Safe Execution**: Always use `logic.gui.engine.get_safe_python_for_gui()` to launch GUIs to ensure compatibility with sandboxed environments (like Cursor terminal).

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

By following this architecture, you ensure that the project remains robust, maintainable, and "agent-friendly." Good luck!

