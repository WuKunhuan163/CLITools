# iCloudPD Tool Enhancement: Agent Guide

## Core Features for Agents

### 1. Robustness & Error Recovery
- **Stall Detection**: If any stage (Scanning, Gathering, Downloading) hangs for more than 30 seconds, the tool triggers a `StallError` and enters an auto-retry loop.
- **Auto-Retry Loop**: The tool will wait for escalating durations (10m, 15m, 20m... up to 1h) before retrying the stalled operation. This handles temporary iCloud service outages or network disconnects.
- **Global Timeout**: Use `--timeout` to control the sensitivity of stall detection.

### 2. Timezone Management
- **Resolver**: Supports IANA zones (e.g., `Asia/Shanghai`), major city names (e.g., `New_York`, `Beijing`), and UTC offsets (e.g., `UTC+8`, `+0530`).
- **Getter**: Run `iCloudPD --timezone` to see the current resolved timezone and UTC offset.
- **IP Detection**: `--timezone None` will attempt to detect the timezone based on the public IP.

### 3. UI & Progress Logic
- **Accurate ETA**: The progress bar calculates ETA based ONLY on the remaining items to be processed from iCloud. If items are found in the gather cache or local download folder, they are treated as "already completed" for the purpose of the overall concept, but excluded from the rate calculation.
- **Alphabetical Summary**: When the tool finish or is interrupted (Ctrl+C), it prints a list of successfully downloaded photos sorted alphabetically by their final path.

### 4. Local Integration
- **Local Photos Library**: Use `--local-photos` to point to a `.photoslibrary`. The tool will read the internal SQLite database to match iCloud assets by ID, avoiding redundant downloads and correctly handling local timezone offsets.

## Operational Best Practices

### Signal Handling
- The tool uses a global SIGINT handler. If the user interrupts, it will print a summary of work completed and exit with code 130.
- **Clean Exit**: `os._exit(130)` is used to bypass standard cleanup if it might hang, ensuring the terminal is restored via the `KeyboardSuppressor`'s `atexit` hook.

### Progress Reporting
- **Sequential Stages**: Use `ProgressTuringMachine` for Scan and Gather stages.
- **Parallel Tasks**: Use `ParallelWorkerPool` for the Download stage.
- **Updates**: Use `stage.refresh()` for live status updates. Avoid `print()` inside active stages.

### Cache Management
- **Scan Cache**: `data/scan/<apple_id>/photos_cache.json` stores basic metadata.
- **Gather Cache**: `full_record` field in the same JSON stores detailed asset metadata (including download URLs).
- **Gather Incremental Save**: Metadata is saved every 100 items during the gathering loop to prevent progress loss.

## Developer Logic Chain
1. **Resolve Timezone**: Convert user input or detected IP to a `ZoneInfo` object.
2. **Scan**: Fetch high-level asset list from iCloud (or use cache).
3. **Filter**: Apply date, media type, and regex filters.
4. **Local Match**: (Optional) Check local `.photoslibrary` for existing assets.
5. **Gather**: Fetch full metadata for remote-only assets (using cache where possible).
6. **Download**: Use parallel workers to fetch files from iCloud URLs.
7. **Summary**: Provide alphabetical list of downloaded items.
