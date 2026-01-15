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
  - `PYTHON --py-install <version>`: Install a specific version from the local repository branch.

## Supported Versions
Currently deployed versions (automatically matched to your OS):
- `python3.8.3` (Default)
- `python3.8.2`, `python3.7.7` (Updated release)
- `python3.10.19`
- `python3.7.5`, `python3.7.4`, `python3.7.3` (Available for macos, linux64, linux64-musl, windows-amd64, windows-x86)

## Implementation Details
### Standalone Environment
Python versions are stored in `proj/install/`. Each installation includes:
- `install/`: The self-contained Python environment.
- `PYTHON.json`: Build manifest with detailed metadata.
- `README.md`: Instructions for manual download and extraction.

### Automatic System Detection
The tool automatically detects your OS and kernel to select the best-matching build. For example, on a Mac, `PYTHON @3.7` will resolve to `python3.7.3-macos`.

### Proxy Logic
All arguments not captured by the manager are passed directly to the selected Python executable. When running a standalone build, `PYTHONHOME` and `PATH` are automatically configured to avoid library conflicts and warnings.

## Language Support
Includes `proj.language_utils` for tool localization based on the `TOOL_LANGUAGE` environment variable.
