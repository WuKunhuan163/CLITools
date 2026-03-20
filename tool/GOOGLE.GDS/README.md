# GOOGLE.GDS (Google Drive Shell)

GOOGLE.GDS replicates a local shell environment bound to Google Drive's file system.
It allows file operations (ls, cat, read, grep, edit), virtual environments, and
background execution — all synchronized through Google Drive as the storage layer.

> **Note**: This tool was originally designed to automate Google Colab as a remote
> execution backend. The MCP/CDP browser automation features that controlled Colab
> have been **disabled** due to potential violations of Google's Terms of Service
> (automated interaction with the Colab web UI). The core Google Drive API-based
> functionality (file access, service account management) remains fully functional.

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

### `GDS setup-tutorial`
Runs a step-by-step interactive GUI to guide you through:
1. Creating a Google Cloud project.
2. Enabling the Google Drive API.
3. Creating a Service Account and generating a JSON key.
4. Sharing target Google Drive folders with the Service Account.
5. Verifying access.

### `GDS remount`
Generates a secure Python script for Google Colab. 
- **Automated Verification**: Uses the Google Drive API to verify that the mount is truly synchronized before finishing.
- **Automatic Clipboard**: On macOS, the script is automatically copied to your clipboard.
- **Fingerprint Protection**: Creates a unique fingerprint file on Google Drive to validate subsequent commands.

### `GDS <COMMAND>`
Executes a command on the remote Colab instance.
- **Default**: Generates a Bash script to be run in the Colab Terminal.
- **--python**: Generates an equivalent Python script to be run in a Colab code cell.
- **Automatic Feedback**: Captures stdout, stderr, and exit codes, displaying them locally upon completion.

### `GDS --raw <COMMAND>`
Executes a command on the remote Colab instance with real-time output visibility.
- Output is displayed directly in the Colab terminal AND captured to a result file on Drive.
- The command is injected directly (no special translation like `ls` -> detailed listing). Remote path expansion (`~`, `@`) and venv prefix are still applied.
- The terminal clears and shows "Finished" when done, matching the normal command experience.
- Clicking Finished retrieves the captured result via Drive API; clicking Feedback opens USERINPUT for the user to provide text feedback directly.

### `GDS --no-capture <COMMAND>`
Executes a command on the remote Colab instance without capturing output.
- Output goes directly to the Colab terminal with no result file.
- Suitable for `pip install`, long-running tasks, or commands that produce large output where capture is impractical.
- The GUI window only shows Copy Script and Finished buttons (no Feedback, since there is no result to download).
- The command is injected directly (same as `--raw`).

### `GDS ls [-l]`
Lists files in the target Google Drive folder.
- **Default**: Shows only names (bash-style).
- **-l**: Shows full details including File ID and MIME Type.

### `GDS cat <FILE_ID>`
Displays the content of a remote file.

### `GDS read <file> [start] [end] [--force]`
Displays remote file contents with line numbers.
- **Default**: Reads via Google Drive API (cached).
- **--force**: Reads via remote `cat` command (bypasses API cache).
- **start/end**: Optional line range to display.

### `GDS grep <pattern> <file> [options]`
Searches for regex patterns in remote files.
- **-i**: Case-insensitive search.
- **-c**: Count matching lines only.
- **-v**: Invert match (show non-matching lines).

### `GDS linter <file> [--language <lang>]`
Lints a remote file locally by downloading via API and running local linters.
- **Python** (.py): pyflakes
- **JSON** (.json): json.load validation
- **Shell** (.sh): shellcheck
- **JS/TS** (.js/.ts): eslint

### `GDS edit <file> <json_spec> [--preview] [--backup]`
Edits remote files using a JSON replacement specification.
- **json_spec**: `[["old_text", "new_text"], ...]` or `[[[start, end], "replacement"], ...]`
- **--preview**: Show diff without applying changes.
- **--backup**: Create a timestamped backup before editing.

### `GDS venv <action> [name ...]`
Manages Python virtual environments in the remote environment (`@/venv/`).
- `--create <name>`: Create a new virtual environment directory.
- `--delete <name>`: Delete an environment (respects protection).
- `--activate <name>`: Activate — sets PYTHONPATH for all subsequent remote commands.
- `--deactivate`: Return to base environment.
- `--list`: List all environments (marks active with `*`).
- `--current`: Show currently active environment details.
- `--protect <name>`: Prevent accidental deletion.
- `--unprotect <name>`: Remove protection.

### `GDS bg <command>` / `GDS bg --status|--log|--result|--cleanup`
Runs remote commands in the background with status tracking.
- `GDS bg "pip install torch"`: Submit a background task.
- `GDS bg --status [task_id]`: Show task status (all or specific).
- `GDS bg --log <task_id>`: View the task's output log.
- `GDS bg --result <task_id>`: View stdout/stderr result.
- `GDS bg --cleanup [task_id]`: Clean up completed task files.

### `GDS shell <action> [name_or_id]`
Manages logical shells for remote development.
- `list`: Shows all available shells and their status.
- `create <name>`: Initializes a new logical shell.
- `switch <id>`: Switches the active remote context.
- `info [id]`: Shows detailed information about a shell.

### `GDS status`
Shows the current active shell and its remote configuration.

### MCP Browser Integration (DISABLED — ToS Risk)

> **WARNING**: The following MCP/CDP browser automation features have been
> **disabled**. Automated interaction with Google Colab's web interface may
> violate [Google Colab's Terms of Service](https://research.google.com/colaboratory/faq.html),
> specifically the prohibition on automated/programmatic access to the service.
> These commands are preserved for reference but will raise an error if invoked.

<!--
#### `GDS --mcp boot`
Launches debug Chrome and opens a Colab tab (or reuses an existing one).

#### `GDS --mcp-remount`
Fully automated Google Drive remount via CDP. Injects the remount script into a Colab cell, handles the OAuth consent dialog and popup automatically, waits for completion, and verifies the result via Drive API. Uses a 4-stage Turing machine: inject -> OAuth -> wait -> verify. A GUI fallback window opens during execution with "Copy Script" and "Feedback" buttons; it auto-closes on success and stays open on failure for manual intervention.

#### `GDS <command> --mcp [--json]`
Generates an MCP workflow for browser-based execution.
- Default output: compact cheat sheet (hash, URL, cell code, marker).
- `--json`: Full structured workflow with step-by-step browser instructions.
- Flow: GDS opens GUI window (copies script to clipboard) -> agent pastes in Colab cell -> executes -> sends `GDS --gui-submit` to close GUI.

#### `GDS --gui-submit [--id <id>]`
Remotely submits (clicks "Finished" on) the GDS interaction window.
- `--gui-cancel`: Cancel the interaction.
- `--gui-stop`: Terminate the interaction.
- `--gui-add-time`: Add 60s to the interaction timeout.

#### `GDS --mcp-create <type> [folder] [--name <name>]`
Creates a Google Drive native file (Colab, Docs, Sheets, etc.) via browser.

#### `GDS --mcp-upload <local_path> [folder]`
Uploads a local file to Google Drive via browser.
-->

### `GDS --reconnection [status|config|reset]`
Manages the API reconnection (auto-remount) mechanism.
- `status`: Show current command counter, thresholds, and flag states.
- `config <count> <duration>`: Set thresholds (default: 50 commands / 300s).
- `reset`: Clear counter and remount flags.

When thresholds are exceeded (command count or single-command duration), the next remote command will auto-trigger `GDS --remount` before execution.

### MCP-Mode Mount Pre-Check (DISABLED — ToS Risk)

> This feature relied on CDP/MCP browser automation and has been disabled.
> See "MCP Browser Integration" above for details.

## Data Locations
- **Config**: `data/config.json`
- **Keys**: `data/google_cloud_console/console_key.json`
- **Shell State**: `tool/GOOGLE.GDS/data/shell_state.json`
- **Reconnection State**: `tool/GOOGLE.GDS/data/run/reconnection_*.json`
- **Debug Logs**: `tool/GOOGLE.GDS/data/log/` (Turing Machine and Drive API logs), `tmp/remount_debug.log` (CDP remount debug)
