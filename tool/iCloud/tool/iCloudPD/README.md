# iCloudPD Subtool

A powerful, parallelized iCloud photo and video downloader. This tool is designed to work seamlessly within the `iCloud` ecosystem.

## Features

- **Parallel Downloads**: Utilizes multiple workers (default 3) to download assets concurrently, significantly speeding up the process.
- **Dynamic Progress**: Real-time single-line progress display showing active downloads and overall completion percentage.
- **Robust Caching**: Scans and caches your entire iCloud library metadata locally, allowing for fast filtering and incremental downloads.
- **Date Range Filtering**: Download assets within specific dates using `--since` and `--before` (YYYY-MM-DD).
- **Subtool Integration**: Inherits authentication and session management from the parent `iCloud` tool.

## Usage

### Basic Download
Download all photos to the current directory:
```bash
iCloudPD
```

### Download Specific Date Range
Download photos from April 19, 2024:
```bash
iCloudPD --since 2024-04-19 --before 2024-04-20
```

### Advanced Options
- `--apple-id <email>`: Pre-fill your Apple ID for authentication.
- `--output <dir>`: Specify a custom directory for downloads (default is `.`).
- `--workers <n>`: Set the number of parallel download workers (default 3).
- `--force-rescan`: Bypass the local cache and re-scan the iCloud library.

## Integration with iCloud Tool
`iCloudPD` is managed as a subtool. You can install it via:
```bash
iCloud install iCloudPD
```
Or run it directly if the parent tool is in your `PATH`.
