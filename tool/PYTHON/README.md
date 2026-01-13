# PYTHON Tool

## Description
This tool provides a managed, standalone Python 3.10 environment to ensure compatibility for GUI tools (like USERINPUT) and other dependency-heavy utilities.

## Usage
- **As a proxy**: Use 'PYTHON <args>' to execute commands using the managed Python environment.
- **As a utility library**: Other tools can import 'proj.utils' or 'proj.language_utils' to leverage shared functionality.

## Managed Installations
Python versions are stored in 'proj/installations/'. Supported versions include:
- python3.10.19 (Default)
- python3.11.14
- python3.12.12
- python3.13.11
- python3.14.2

Each installation includes:
- `install/`: The actual Python environment.
- `PYTHON.json`: A comprehensive build manifest provided by `python-build-standalone`. It contains detailed metadata about the build process, configuration variables (`python_config_vars`), library links, and extension module information. This is useful for debugging and for tools that need to understand the underlying Python configuration.
- `licenses/`: License information for CPython and its dependencies.

## Deployment Strategy
To avoid remote access issues, standalone Python distributions are "deployed" by adding them to the `tool` branch of this repository. When a specific version is requested (via `--py-install`), it is retrieved locally from that branch using `git checkout`.

## Language Support
Includes 'proj.language_utils' for tool localization based on the 'TOOL_LANGUAGE' environment variable.
