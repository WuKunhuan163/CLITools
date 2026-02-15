# iCloudPD Subtool

A powerful, parallelized iCloud photo and video downloader. This tool is designed to work seamlessly within the `iCloud` ecosystem.

## Features

- **Extreme Gathering Optimization**: Uses CloudKit `lookup` endpoint to bypass full library scans for specific assets, reducing gathering time from minutes to seconds.
- **Parallel Downloads**: Utilizes multiple workers (default 3) to download assets concurrently, significantly speeding up the process.
- **Automatic Retries**: Each download task includes 3 internal retries to handle network flakiness.
- **Robust Caching**: Scans and caches your entire iCloud library metadata locally in a date-grouped structure (`YYYY-MM-DD`).
- **Incremental Scanning**: Atomically saves metadata after each batch and periodically (every 30s) to prevent data loss.
- **Smart Collision Protection**: Automatically renames files with numeric suffixes (e.g., `IMG_0001_1.JPG`) if multiple photos have the same name on the same day.
- **Flexible Filtering**: 
    - Date range (`--since`, `--before`).
    - Media type (`--only-photos`, `--only-videos`).
    - Extension globbing (`--formats "*.png|*.jpg"`).
    - Path/Name Regex (`--regex "^2026-02-14/"`).
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
- `--force-rescan`: Bypass the local cache and re-scan the iCloud library (Note: `ASCENDING` is newest-first).
- `--no-gui`: Force CLI interaction (useful for remote servers or terminal-only environments).

## Integration with iCloud Tool
`iCloudPD` is managed as a subtool. You can install it via:
```bash
iCloud install iCloudPD
```
Or run it directly if the parent tool is in your `PATH`.
