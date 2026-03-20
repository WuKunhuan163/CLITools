# Python Resource Migration Implementation Report

## Overview
This report documents the implementation of the automated Python resource migration system, designed to synchronize standalone CPython builds from the `astral-sh/python-build-standalone` project to our local project's remote `tool` branch.

## Core Components

### 1. The Migration Engine (`tool/PYTHON/logic/update.py`)
The engine is responsible for:
- **Indexing**: Fetching all release tags via `git ls-remote --tags` and asset metadata via GitHub API or web scraping.
- **Filtering**: Matching assets to our supported platforms (macOS, Linux, Windows) and selecting the best variants (e.g., PGO+LTO builds).
- **Versioning**: Implementing a `TAG:VERSION` syntax for precise targeting of specific releases.
- **Parallelization**: Using a `MultiLineManager` and `TuringWorker` pool to handle concurrent downloads and Git pushes.
- **Git Integration**: Managing the `logic/_/install/resource/PYTHON/data/install/` directory on the `tool` branch, including metadata merging and atomic pushes with rebase-retry logic.

### 2. Audit and Cache System
- **Releases Audit**: `tool/PYTHON/data/_/audit/releases/report_xxx.json` stores a comprehensive matrix of versions, releases, and platform mappings.
- **Asset Cache**: `tool/PYTHON/data/_/audit/assets/assets_xxx.json` caches per-tag asset lists to avoid GitHub API rate limits.
- **Failure Tracking**: `tool/PYTHON/data/_/audit/failures/` logs detailed error reports for failed migrations.

### 3. Verification and Update Logic
- **`PYTHON.json` Metadata**: Every migrated version includes a `release` field in its manifest.
- **Automatic Updates**: When `PYTHON --py-update` is run without a forced tag, the system compares the local `release` date with the latest available from the remote index. If a newer release is found, it automatically triggers a migration.

## Migration Workflow
The following workflow was used to migrate the entire Python asset library:

1. **Scan and Index**:
   ```bash
   PYTHON --py-update --list
   ```
2. **Calculate Latest Versions**:
   The `report_xxx.json` is analyzed to extract the lexicographically maximum (latest) release tag for each unique `VERSION-PLATFORM` identifier.
3. **Batch Migration**:
   A temporary batch script (`/tmp/migrate_batch.py`) executes migration commands in chunks of 5 using the optimized `TAG:VERSION` syntax:
   ```bash
   PYTHON --py-update --version "20251007:3.12.11-windows-amd64", "20260127:3.12.12-linux64", ... --concurrency 3
   ```

## Key Optimization: Tag Grouping
To minimize remote overhead, the migration engine groups assets by their target release tag. This allows a single fetch operation to retrieve metadata for all assets in a batch, followed by parallelized downloads and serial Git commits.

## Multi-line Progress Display
The system utilizes a custom `MultiLineManager` to provide real-time, erasable progress bars for each worker. Content is dynamically truncated to the current terminal width to prevent line wrapping and ensure a clean UI even in narrow terminals.

