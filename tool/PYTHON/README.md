# PYTHON Tool

## Description
This tool provides a managed, standalone Python environment to ensure compatibility across different tools and projects. It supports multiple Python versions and automatically selects the appropriate build for your current operating system.

## Usage
- **As a proxy**: Use `PYTHON <args>` to execute commands using the managed Python environment.
- **Specifying Version**:
  - **Shorthand**: Use `@3.x` as the first argument (e.g., `PYTHON @3.7 -c "..."`).
  - **Command flag**: Use `--py-version <version>`.
  - **Environment variable**: Set `PY_VERSION` (e.g., `PY_VERSION=python3.7.3-macos PYTHON ...`).
- **Management**:
  - `PYTHON --py-list`: List supported and installed versions.
  - `PYTHON --py-install <version>`: Install a specific version from the project's remote `tool` branch.
  - `PYTHON --py-update`: Advanced resource migration and maintenance (for developers).
    - `--list`: Scan GitHub releases (`astral-sh/python-build-standalone`) and generate audit reports.
    - `--version <v>`: Migrate specific versions (supports comma-separated lists and `TAG:VERSION` syntax).
    - `--tag <t>`: Specify a release tag for migration.
    - `--all-latest`: Automatically migrate the latest release for all unique version-platform pairs.
    - `--concurrency <n>`: Set parallel download/push workers (default: 1).

## Supported Versions
Automatically matched to your OS and architecture:
- `3.13.x`
- `3.12.x`
- `3.11.x`
- `3.10.x`
- `3.9.x`
- `3.8.x`
- `3.7.x`
- And many legacy/maintenance variants. See `PYTHON --py-list` for details.

## Implementation Details
### Standalone Environment
Python versions are stored in `data/install/`. Each installation includes:
- `install/`: The self-contained Python environment.
- `PYTHON.json`: Build manifest with detailed metadata, including the `release` tag for update tracking.

### Automatic System Detection
The tool automatically detects your OS and kernel to select the best-matching build. For example, on a Mac, `PYTHON @3.7` will resolve to `3.7.7-macos`.

### Proxy Logic
All arguments not captured by the manager are passed directly to the selected Python executable. When running a standalone build, `PYTHONHOME` and `PATH` are automatically configured to avoid library conflicts.

## Developer Documentation
For details on the migration engine and audit system, see [Migration Implementation Report](report/migration_implementation.md).
