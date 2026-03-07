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

### 4. Implementation Details
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

### Debugging Timeouts
If `wait_for_gdrive_file` times out:
1. Check `tool/GOOGLE.GCS/tmp/gcs_debug.log`.
2. Ensure the remote script was actually executed and finished (printed the "Finished" message).
3. Verify that Google Drive is mounted on Colab (`/content/drive/MyDrive` exists).
