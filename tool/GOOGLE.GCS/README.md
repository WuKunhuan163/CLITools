# GOOGLE.GCS (Google Drive Remote Controller)

GOOGLE.GCS is a powerful tool designed to facilitate remote execution on Google Colab using Google Drive as a synchronization layer. It manages service account credentials, provides a bridge for remote file access, and simplifies the Colab environment setup.

## Features

- **Colab Remote Control**: Easily mount Google Drive on a remote Colab instance and verify access securely.
- **Remote Command Execution**: Execute any shell command on the remote Colab instance and capture results locally.
- **File Operations**: `read` (with line numbers), `grep` (regex search), `linter` (local lint), `edit` (remote text replacement via JSON spec).
- **Virtual Environments**: Create, activate, and manage isolated Python environments on the remote. Active venvs inject `PYTHONPATH` into all remote commands.
- **Background Execution**: Run long-running commands (pip install, git clone) in background with status/log/result tracking.
- **Service Account Management**: Handles the complex setup of Google Cloud service accounts and keys.
- **Logical Shells**: Supports multiple "logical shells," each with its own remote context (CWD, virtualenv, etc.).
- **Bash-style Interface**: Provides standard `ls`, `cat`, `read`, `grep`, and other commands that behave like native shell tools.
- **Robust Verification**: Implements a fingerprint mechanism to ensure local and remote sessions are correctly synced.

## Commands

### `GCS setup-tutorial`
Runs a step-by-step interactive GUI to guide you through:
1. Creating a Google Cloud project.
2. Enabling the Google Drive API.
3. Creating a Service Account and generating a JSON key.
4. Sharing target Google Drive folders with the Service Account.
5. Verifying access.

### `GCS remount`
Generates a secure Python script for Google Colab. 
- **Automated Verification**: Uses the Google Drive API to verify that the mount is truly synchronized before finishing.
- **Automatic Clipboard**: On macOS, the script is automatically copied to your clipboard.
- **Fingerprint Protection**: Creates a unique fingerprint file on Google Drive to validate subsequent commands.

### `GCS <COMMAND>`
Executes a command on the remote Colab instance.
- **Default**: Generates a Bash script to be run in the Colab Terminal.
- **--python**: Generates an equivalent Python script to be run in a Colab code cell.
- **Automatic Feedback**: Captures stdout, stderr, and exit codes, displaying them locally upon completion.

### `GCS --raw <COMMAND>`
Executes a command on the remote Colab instance with real-time output visibility.
- Output is displayed directly in the Colab terminal AND captured to a result file on Drive.
- The command is injected directly (no special translation like `ls` -> detailed listing). Remote path expansion (`~`, `@`) and venv prefix are still applied.
- The terminal clears and shows "Finished" when done, matching the normal command experience.
- Clicking Feedback downloads the captured result locally; clicking Finished retrieves it via Drive API.

### `GCS --no-capture <COMMAND>`
Executes a command on the remote Colab instance without capturing output.
- Output goes directly to the Colab terminal with no result file.
- Suitable for `pip install`, long-running tasks, or commands that produce large output where capture is impractical.
- The GUI window only shows Copy Script and Finished buttons (no Feedback, since there is no result to download).
- The command is injected directly (same as `--raw`).

### `GCS ls [-l]`
Lists files in the target Google Drive folder.
- **Default**: Shows only names (bash-style).
- **-l**: Shows full details including File ID and MIME Type.

### `GCS cat <FILE_ID>`
Displays the content of a remote file.

### `GCS read <file> [start] [end] [--force]`
Displays remote file contents with line numbers.
- **Default**: Reads via Google Drive API (cached).
- **--force**: Reads via remote `cat` command (bypasses API cache).
- **start/end**: Optional line range to display.

### `GCS grep <pattern> <file> [options]`
Searches for regex patterns in remote files.
- **-i**: Case-insensitive search.
- **-c**: Count matching lines only.
- **-v**: Invert match (show non-matching lines).

### `GCS linter <file> [--language <lang>]`
Lints a remote file locally by downloading via API and running local linters.
- **Python** (.py): pyflakes
- **JSON** (.json): json.load validation
- **Shell** (.sh): shellcheck
- **JS/TS** (.js/.ts): eslint

### `GCS edit <file> <json_spec> [--preview] [--backup]`
Edits remote files using a JSON replacement specification.
- **json_spec**: `[["old_text", "new_text"], ...]` or `[[[start, end], "replacement"], ...]`
- **--preview**: Show diff without applying changes.
- **--backup**: Create a timestamped backup before editing.

### `GCS venv <action> [name ...]`
Manages Python virtual environments in the remote environment (`@/venv/`).
- `--create <name>`: Create a new virtual environment directory.
- `--delete <name>`: Delete an environment (respects protection).
- `--activate <name>`: Activate — sets PYTHONPATH for all subsequent remote commands.
- `--deactivate`: Return to base environment.
- `--list`: List all environments (marks active with `*`).
- `--current`: Show currently active environment details.
- `--protect <name>`: Prevent accidental deletion.
- `--unprotect <name>`: Remove protection.

### `GCS bg <command>` / `GCS bg --status|--log|--result|--cleanup`
Runs remote commands in the background with status tracking.
- `GCS bg "pip install torch"`: Submit a background task.
- `GCS bg --status [task_id]`: Show task status (all or specific).
- `GCS bg --log <task_id>`: View the task's output log.
- `GCS bg --result <task_id>`: View stdout/stderr result.
- `GCS bg --cleanup [task_id]`: Clean up completed task files.

### `GCS shell <action> [name_or_id]`
Manages logical shells for remote development.
- `list`: Shows all available shells and their status.
- `create <name>`: Initializes a new logical shell.
- `switch <id>`: Switches the active remote context.
- `info [id]`: Shows detailed information about a shell.

### `GCS status`
Shows the current active shell and its remote configuration.

### MCP Browser Integration

When running in an MCP-capable environment (e.g., Cursor IDE), GCS commands can be executed directly in Colab via the built-in browser.

#### `GCS <command> --mcp [--json]`
Generates an MCP workflow for browser-based execution.
- Default output: compact cheat sheet (hash, URL, cell code, marker).
- `--json`: Full structured workflow with step-by-step browser instructions.
- Flow: GCS opens GUI window (copies script to clipboard) -> agent pastes in Colab cell -> executes -> sends `GCS --gui-submit` to close GUI.

#### `GCS --gui-submit [--id <id>]`
Remotely submits (clicks "Finished" on) the GCS interaction window.
- `--gui-cancel`: Cancel the interaction.
- `--gui-stop`: Terminate the interaction.
- `--gui-add-time`: Add 60s to the interaction timeout.

#### `GCS --mcp-create <type> [folder] [--name <name>]`
Creates a Google Drive native file (Colab, Docs, Sheets, etc.) via browser.

#### `GCS --mcp-upload <local_path> [folder]`
Uploads a local file to Google Drive via browser.

## Data Locations
- **Config**: `data/config.json`
- **Keys**: `data/google_cloud_console/console_key.json`
- **Shell State**: `tool/GOOGLE.GCS/data/shell_state.json`
- **Debug Logs**: `tool/GOOGLE.GCS/tmp/gcs_debug.log`
