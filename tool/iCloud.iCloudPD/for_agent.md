# iCloudPD Tool Enhancement

## Current Status
- [x] Support local MacBook Photos Library (`.photoslibrary`).
- [x] Custom filename and directory grouping using placeholders.
- [x] Performance optimization for gathering stage using persistent cache (`full_record` in `photos_cache.json`).
- [x] Robust Ctrl+C (SIGINT) handling with terminal restoration and immediate exit (`os._exit(130)`).
- [x] Incremental saving of metadata during gathering phase (every 100 items).
- [x] Corrected progress reporting logic in `ParallelWorkerPool`.
- [x] Integrated interactive CLI prompts (password, 2FA) into Turing Machine status flow.

## Developer Best Practices: Turing Machine & Signal Management

### 1. Robust Signal Handling
- **Problem**: Python `KeyboardInterrupt` can sometimes be caught by unintended `try...except Exception` blocks or swallowed by background threads, preventing clean exits.
- **Solution**:
    - **Global Handler**: Always register a global `signal.signal(signal.SIGINT, handler)` in `main.py`. This handler should print a red "Operation cancelled" message and use `os._exit(130)` to force an immediate termination.
    - **Atomic Exits**: In `ProgressTuringMachine` and `ParallelWorkerPool`, use `os._exit(130)` inside `KeyboardInterrupt` catch blocks to bypass standard exception bubbling.

### 2. Responsible Keyboard Suppression
- **KeyboardSuppressor**: Uses `termios` to disable `ECHO` for clean terminal output while keeping `ISIG` and `ICANON` enabled.
- **Signal Compatibility**: Never disable `ISIG` if you want the user to be able to use `Ctrl+C`.
- **Handling Interactive Input**:
    - When your tool needs interactive user input (e.g., `input()`, `getpass()`) while a Turing Machine is running, you **MUST** temporarily stop the suppressor.
    - **Pattern**:
      ```python
      was_suppressed = suppressor.is_suppressed()
      if was_suppressed: suppressor.stop()
      try:
          user_data = input("Prompt: ")
      finally:
          if was_suppressed: suppressor.start()
      ```
    - This ensures the user can see their input and the terminal state is correctly restored if they interrupt during the prompt.

### 3. Turing Machine Status Updates
- **Avoid Manual Prints**: Do not use `print()` or `sys.stdout.write()` for status updates when a Turing Machine or `ParallelWorkerPool` is active. Instead, update `stage.active_name` and call `stage.refresh()`.
- **Status Integration**: If an interactive action is needed, update the machine's status to reflect the wait (e.g., `stage.active_name = "Waiting for password..."`) before clearing the current line and showing the prompt.
- **Batch Updates**: For high-throughput tasks, update the status at reasonable intervals (e.g., every 10 or 100 items) to avoid excessive terminal flickering.

## Logic Principle: Gathering Cache
The "Gathering" stage fetches full metadata (like download URLs) for assets not found locally.
- **Cache**: results are saved in `tool/iCloud.iCloudPD/data/scan/<id>/photos_cache.json` under `full_record`.
- **Incremental Progress**: The gathering loop now saves the cache after each batch of 100 lookups.
- **Fast Mode**: Subsequent runs skip iCloud lookups for any asset that has a `full_record` in the cache.

## Troubleshooting
- **Zombie Terminals**: If a script exits but your terminal no longer echoes what you type, run `stty echo` to manually restore it. Our `KeyboardSuppressor` includes an `atexit` hook to prevent this, but manual runs might still hit it if crashed elsewhere.
- **Debug Logs**: Prefer logging to `/tmp/icloudpd_debug.log` for tracing complex logic chains during development.
