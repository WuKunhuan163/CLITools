# GOOGLE.GDS Agent Guide

GOOGLE.GDS (Google Drive Shell) replicates a local shell environment bound to Google Drive.
Core features: file operations (ls, cat, read, grep, edit), virtual environments, and
background execution via Google Drive API + service account credentials.

> **MCP/CDP browser automation features are DISABLED.** Automated control of
> Google Colab's web UI may violate Google's ToS. All `--mcp*` commands,
> CDP boot, and browser-based remount have been disabled. Use the Google Drive
> API-based workflows (service account, `GDS remount` manual script) instead.

## Critical Concepts

### 1. Synchronization Layer
Synchronization relies on a `REMOTE_ROOT` and `REMOTE_ENV` structure in Google Drive. 
- `REMOTE_ENV/tmp/`: Used for "handshake" files (like `remount_result_*.json` and `.gds_mount_fingerprint_*`). Keeping temp files in `REMOTE_ENV` keeps `REMOTE_ROOT` clean for user data.
- **New Session Logic**: Always check for the `.gds_mount_fingerprint_{hash}` file. If it's missing, the Colab session is likely stale or unmounted.

### 2. The Verification Loop
When generating a `remount` or command script, we always include a verification phase.
- **Remote Script**: Writes a JSON result file to `tmp/`.
- **Local Tool**: Uses `wait_for_gdrive_file` to poll the Google Drive API.
- **Performance**: We use folder-ID based queries and random `quotaUser` to bypass Google Drive's aggressive server-side caching and slow search indexing.

### 3. Logical Shells
Logical shells are identified by a `{timestamp}_{6-digit-hash}` ID. 
- Use `GDS shell create <name>` to start a new project.
- Use `GDS shell list` to find IDs for switching.
- Each shell tracks its own `shell_type` (default: `bash`). Use `GDS --shell type` to check or `GDS --shell type zsh` to switch.
- Use `GDS --shell install zsh` to install alternative shells (zsh, fish) on the remote Colab environment. The binary is persisted at `REMOTE_ENV/shell/<name>/bin/<name>` to survive runtime restarts.

### 4. Raw Mode
`GDS --raw <command>` uses the same result capture pipeline as normal commands:
- The remote script uses `tee` to both display output in real-time AND write it to capture files.
- A result JSON file is written to `REMOTE_ENV/tmp/` just like normal mode.
- The verify stage uses `wait_for_gdrive_file` to download results, identical to normal commands.
- The only difference is that the user's command is injected directly (no special command translation). Remote path expansion (`~`, `@`) and venv prefixes are still applied.

### 4b. No-Capture Mode
`GDS --no-capture <command>` is a variant of raw mode for commands where capturing output is impractical:
- Output goes directly to the Colab terminal (no `tee`, no temp files, no result JSON).
- The verify stage is skipped entirely since there is no result file.
- The GUI only shows Copy Script and Finished buttons (no Feedback).
- Use cases: `pip install`, `apt-get`, `git clone`, or any long-running task with heavy output.
- Implementation: `_generate_no_capture_script` in `raw_cmd.py` produces a minimal script that validates mount, changes directory, runs the command, and shows a "Finished" message.

### 5. MCP Browser Mode (DISABLED — ToS Risk)

> **All MCP/CDP browser automation for Colab has been disabled.**
> Automated control of Google Colab's web interface may violate
> [Google's Terms of Service](https://research.google.com/colaboratory/faq.html).
> The `--mcp*` commands, CDP boot, browser-based remount, and cell injection
> are commented out in the source code but preserved for reference.
> Use manual workflows (copy script from GUI, paste into Colab manually) instead.

### 6. Implementation Details
- **IPv4 Enforcement**: The tool forces IPv4 for Google API calls to avoid 60-second timeouts caused by macOS IPv6 fallback issues.
- **GUI Blueprints**: Uses `ButtonBarWindow` for simple multi-option interactions.
- **Remote CWD**: The generated scripts automatically `mkdir -p` the remote working directory and `tmp` folder.

### 7. API Reconnection Manager
The tool automatically tracks command execution count and duration. When thresholds are exceeded, it triggers `GDS --remount` before the next command.

- **Thresholds**: Default 50 commands or 300s single-command duration. Configure with `GDS --reconnection config <count> <duration>`.
- **State files**: `tool/GOOGLE.GDS/data/run/reconnection_counter.json`, `reconnection_config.json`, `remount_required.flag`, `remount_in_progress.lock`.
- **Pre-check flow**: Before every remote command, the reconnection manager checks the counter and flag. If remount is needed, it's triggered automatically.
- **Lock coordination**: A lock file prevents concurrent remount attempts. The lock has PID-based liveness checks and a 5-minute expiry.

### 8. MCP-Mode Mount Pre-Check (DISABLED — ToS Risk)

> This feature relied on CDP browser automation and has been disabled.
> See section 5 above for details.

## Common Operations

### Checking Remote Status
Always run `GDS status` before initiating remote commands to ensure you are in the correct shell and the remote CWD is as expected.

### Fixing "Unsynchronized" Drive
If a file exists on Colab but not locally (or vice-versa), advise the user to:
1. Restart the Colab runtime.
2. Run `GDS remount` again.
3. Wait for the API verification loop to complete in the remount GUI.

### Debugging Timeouts
If `wait_for_gdrive_file` times out:
1. Check `tool/GOOGLE.GDS/data/log/wait_for_file_debug.log` for Drive API polling details.
2. Check `tmp/remount_debug.log` for CDP remount stage debug output.
3. Ensure the remote script was actually executed and finished (printed the "Finished" message).
4. Verify that Google Drive is mounted on Colab (`/content/drive/MyDrive` exists).

## Development Lessons (2026-03-05)

### GUI subprocess lifecycle in MCP mode
When launching a fallback GUI as a background subprocess during automated operations:
- Use `start_new_session=True` to prevent SIGINT propagation from parent.
- Use file-based signaling (`{pid}.submit` flag files) for inter-process auto-close.
- Always clean up temporary script files, but leave the GUI alive on failure for user fallback.
- Pass mode flags (e.g., `--mcp`) to control button visibility and instruction text.

### Documentation drift
After modifying code, always cross-check `README.md` and `AGENT.md` for:
- File path references (e.g., `REMOTE_ENV/tmp/` vs. `REMOTE_ROOT/tmp/`).
- Button/UI behavior descriptions matching actual code.
- Markdown heading hierarchy (sections can silently break when new content is inserted).

### Debugging CDP Failures
When a CDP-mode command fails, the Turing machine now shows specific error reasons:
- **"Google Drive not mounted"**: Run `GDS --remount` to re-mount.
- **"Mount fingerprint mismatch"**: Stale session. Run `GDS --remount` to refresh.
- **"Colab notebook tab not found"**: Run `GDS --mcp boot` to start Chrome CDP.
- **"CDP connection failed"**: Verify Chrome is running with `--remote-debugging-port=9222`.
- **"Remote execution timed out"**: Command exceeded the timeout. Consider `GDS --raw` for long tasks.
