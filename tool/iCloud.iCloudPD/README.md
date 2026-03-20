# iCloudPD Subtool

A powerful, parallelized iCloud photo and video downloader. This tool is designed to work seamlessly within the `iCloud` ecosystem.

## Features

- **Extreme Gathering Optimization**: Uses CloudKit `lookup` endpoint to bypass full library scans for specific assets, reducing gathering time from minutes to seconds.
- **Parallel Downloads**: Utilizes multiple workers (default 3) to download assets concurrently, significantly speeding up the process.
- **Automatic Retries**: Each download task includes 3 internal retries to handle network flakiness.
- **Robust Caching**: Scans and caches your entire iCloud library metadata locally in a date-grouped structure (`YYYY-MM-DD`).
- **Incremental Progress**: Incremental saving of metadata during the gathering phase ensures progress is saved even if interrupted.
- **Safe Interrupts**: Full support for `Ctrl+C` (SIGINT) at any stage (authentication, gathering, downloading). The tool ensures a clean exit, restores terminal settings, and provides an alphabetical download summary.
- **Interactive Authentication**: Seamlessly handles password and 2FA prompts in both GUI and CLI modes, with keyboard suppression to protect your input.
- **Incremental Scanning**: Atomically saves metadata after each batch and periodically (every 30s) to prevent data loss.
- **Smart Collision Protection**: Automatically renames files with numeric suffixes (e.g., `IMG_0001_1.JPG`) if multiple photos have the same name on the same day.
- **Flexible Filtering**: 
    - Date range (`--since`, `--before`, `--between`).
    - Media type (`--only-photos`, `--only-videos`).
    - Extension globbing (`--formats "*.png|*.jpg"`).
    - Path/Name Regex (`--regex "^2026-02-14/"`).
- **Timezone Management**: 
    - Use `--timezone Asia/Shanghai` or `--timezone Beijing` (mapped to IANA) for correct date filtering and filename generation.
    - Query current timezone and UTC offset with `iCloudPD --timezone`.
    - Automatically detect via IP with `--timezone None`.
- **Enhanced Reliability**:
    - **Global Timeout**: `--timeout` (default 1800s) applies to Scan, Gather, and Download stages.
    - **Stall Detection**: Automatically detects if progress has stopped for >30s (configurable).
    - **Auto-Retry Loop**: Retries stalled operations with escalating wait times (10m, 15m, 20m... up to 1h).
- **UI/UX Refinements**:
    - **Accurate ETA**: Calculation only includes assets requiring remote work (skips cached/downloaded items).
    - **"Scheduled" Messages**: Uses `Scheduled N photos/videos` phrasing for clarity during gathering.
    - **Summary**: Displays successfully downloaded items in alphabetical order on completion or user interrupt.
- **Local Library Integration**:
    - Use `--local-photos [PATH]` to check a local Apple Photos Library (`.photoslibrary`) before downloading from iCloud.
    - Maps iCloud IDs to local files using the database and resolves local creation times including timezone offsets.
- **GUI & CLI Modes**: Supports both Tkinter-based interactive login and pure CLI interaction (`--no-gui`).

## Usage

### Basic Download
Download all photos to the current directory:
```bash
iCloudPD
```

### Download Specific Date Range
Download photos from February 14, 2026:
```bash
iCloudPD --since 2026-02-14 --before 2026-02-15
```

### Advanced Filtering
Download only PNG videos from 2026 using regex:
```bash
iCloudPD --regex "^2026-" --only-videos --formats "*.png"
```

### Metadata Only
Scan and cache metadata without downloading files:
```bash
iCloudPD --only-scan
```

### Advanced Options
- `--apple-id <email>`: Pre-fill your Apple ID for authentication.
- `--output <dir>`: Specify a custom directory for downloads.
- `--workers <n>`: Set the number of parallel download workers (default 3).
- `--force-rescan`: Bypass the local cache and re-scan the iCloud library.
- `--no-gui`: Force CLI interaction.
- `--timezone <tz>`: Set timezone (IANA, city, or UTC offset).
- `--timeout <seconds>`: Set global stall timeout.

## Integration with iCloud Tool
`iCloudPD` is managed as a subtool. You can install it via:
```bash
iCloud install iCloudPD
```
Or run it directly if the parent tool is in your `PATH`.
