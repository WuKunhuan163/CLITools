# GOOGLE.GCS Agent Guide

This subtool is critical for remote execution flows between the local machine and Google Colab.

## Critical Concepts

### 1. Synchronization Layer
Synchronization relies on a `REMOTE_ROOT` and `REMOTE_ENV` structure in Google Drive. 
- `REMOTE_ROOT/tmp/`: Used for "handshake" files (like `remount_result_*.json` and `.gds_mount_fingerprint_*`).
- **New Session Logic**: Always check for the `.gds_mount_fingerprint_{hash}` file. If it's missing, the Colab session is likely stale or unmounted.

### 2. The Verification Loop
When generating a `remount` or command script, we always include a verification phase.
- **Remote Script**: Writes a JSON result file to `tmp/`.
- **Local Tool**: Uses `wait_for_gdrive_file` to poll the Google Drive API.
- **Performance**: We use folder-ID based queries and random `quotaUser` to bypass Google Drive's aggressive server-side caching and slow search indexing.

### 3. Logical Shells
Logical shells are identified by a `{timestamp}_{6-digit-hash}` ID. 
- Use `GCS shell create <name>` to start a new project.
- Use `GCS shell list` to find IDs for switching.
- Each shell tracks its own `shell_type` (default: `bash`). Use `GCS --shell type` to check or `GCS --shell type zsh` to switch.
- Use `GCS --shell install zsh` to install alternative shells (zsh, fish) on the remote Colab environment. The binary is persisted at `REMOTE_ENV/shell/<name>/bin/<name>` to survive runtime restarts.

### 4. Raw Mode
`GCS --raw <command>` uses the same result capture pipeline as normal commands:
- The remote script uses `tee` to both display output in real-time AND write it to capture files.
- A result JSON file is written to `REMOTE_ROOT/tmp/` just like normal mode.
- The verify stage uses `wait_for_gdrive_file` to download results, identical to normal commands.
- The only difference is that the user's command is injected directly (no special command translation). Remote path expansion (`~`, `@`) and venv prefixes are still applied.

### 4b. No-Capture Mode
`GCS --no-capture <command>` is a variant of raw mode for commands where capturing output is impractical:
- Output goes directly to the Colab terminal (no `tee`, no temp files, no result JSON).
- The verify stage is skipped entirely since there is no result file.
- The GUI only shows Copy Script and Finished buttons (no Feedback).
- Use cases: `pip install`, `apt-get`, `git clone`, or any long-running task with heavy output.
- Implementation: `_generate_no_capture_script` in `raw_cmd.py` produces a minimal script that validates mount, changes directory, runs the command, and shows a "Finished" message.

### 5. MCP Browser Mode
`GCS <command> --mcp` enables browser-based execution in the Cursor IDE built-in browser.

**No dedicated notebook required.** GCS works with any open Colab tab -- the default "Welcome to Colab" page is sufficient. Run `GCS --mcp boot` to ensure a Colab tab is open.

#### Automated Remount
`GCS --mcp-remount` performs a fully automated Google Drive remount via CDP:
1. Injects the remount script into a Colab cell.
2. Detects and clicks the "Connect to Google Drive" dialog if it appears.
3. Navigates OAuth consent popup (clicks "Continue" / "Allow" buttons).
4. Waits for the cell to finish executing.
5. Verifies the mount result via the Drive API (fingerprint file check).

This is a 4-stage Turing machine: inject -> OAuth -> wait -> verify. The OAuth stage auto-skips if the user is already authorized.

#### Manual MCP Workflow
1. Run `GCS <command>` (opens GUI window, auto-copies script to clipboard).
2. Navigate built-in browser to any Colab tab.
3. Create a new cell (Escape -> Ctrl+M -> B), enter edit mode (Enter).
4. Use `browser_type` with `slowly: true` to type the cell code.
5. Press Escape (dismiss autocomplete), then Meta+Enter to execute.
6. Wait for completion marker, then `GCS --gui-submit` to close the GUI.
7. Normal result download resumes.

**Key rules:**
- NEVER use `browser_fill` on Colab cells (breaks CodeMirror).
- NEVER use Meta+V paste (MCP browser has isolated clipboard, doesn't share with system).
- Always create fresh cells rather than editing existing ones.
- Use `browser_type` with `slowly: true` to input code into cells.
- The GUI window stays open as a safety net; fallback to USERINPUT if MCP fails.
- Command hash (8-char uppercase) appears in the window title: `GCS Remote Command [XXXXXXXX]`.
- If "Could not load JavaScript files" error appears, use Runtime -> "Restart session and run all".

**Remote GUI control:**
- `GCS --gui-submit [--id <id>]`: Click "Finished" button externally.
- `GCS --gui-cancel`, `--gui-stop`, `--gui-add-time`: Cancel, stop, or extend timeout.

### 6. Implementation Details
- **IPv4 Enforcement**: The tool forces IPv4 for Google API calls to avoid 60-second timeouts caused by macOS IPv6 fallback issues.
- **GUI Blueprints**: Uses `ButtonBarWindow` for simple multi-option interactions.
- **Remote CWD**: The generated scripts automatically `mkdir -p` the remote working directory and `tmp` folder.

## Common Operations

### Checking Remote Status
Always run `GCS status` before initiating remote commands to ensure you are in the correct shell and the remote CWD is as expected.

### Fixing "Unsynchronized" Drive
If a file exists on Colab but not locally (or vice-versa), advise the user to:
1. Restart the Colab runtime.
2. Run `GCS remount` again.
3. Wait for the API verification loop to complete in the remount GUI.

### 7. API Reconnection Manager
The tool automatically tracks command execution count and duration. When thresholds are exceeded, it triggers `GCS --remount` before the next command.

- **Thresholds**: Default 50 commands or 300s single-command duration. Configure with `GCS --reconnection config <count> <duration>`.
- **State files**: `tool/GOOGLE.GCS/data/run/reconnection_counter.json`, `reconnection_config.json`, `remount_required.flag`, `remount_in_progress.lock`.
- **Pre-check flow**: Before every remote command, the reconnection manager checks the counter and flag. If remount is needed, it's triggered automatically.
- **Lock coordination**: A lock file prevents concurrent remount attempts. The lock has PID-based liveness checks and a 5-minute expiry.

### 8. MCP-Mode Mount Pre-Check
In CDP/MCP mode, `remote.py execute()` performs a lightweight Drive API check for the mount fingerprint file before running any command. If the fingerprint is missing:
1. Auto-remount is triggered via `remount_cmd.execute()`.
2. If remount fails, a clear error message is shown with guidance to run `GCS --remount` manually.
This prevents the "GUI closed unexpectedly" error that previously occurred when Drive was not mounted.

### Debugging Timeouts
If `wait_for_gdrive_file` times out:
1. Check `tool/GOOGLE.GCS/tmp/gcs_debug.log`.
2. Ensure the remote script was actually executed and finished (printed the "Finished" message).
3. Verify that Google Drive is mounted on Colab (`/content/drive/MyDrive` exists).

### Debugging CDP Failures
When a CDP-mode command fails, the Turing machine now shows specific error reasons:
- **"Google Drive not mounted"**: Run `GCS --remount` to re-mount.
- **"Mount fingerprint mismatch"**: Stale session. Run `GCS --remount` to refresh.
- **"Colab notebook tab not found"**: Run `GCS --mcp boot` to start Chrome CDP.
- **"CDP connection failed"**: Verify Chrome is running with `--remote-debugging-port=9222`.
- **"Remote execution timed out"**: Command exceeded the timeout. Consider `GCS --raw` for long tasks.
