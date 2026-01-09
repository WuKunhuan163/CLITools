# PYTHON Tool

## Description
This tool provides a managed, standalone Python 3.10 environment to ensure compatibility for GUI tools (like USERINPUT) and other dependency-heavy utilities.

## Usage
- **As a proxy**: Use 'PYTHON <args>' to execute commands using the managed Python environment.
- **As a utility library**: Other tools can import 'proj.utils' or 'proj.language_utils' to leverage shared functionality.

## Managed Installations
Python versions are stored in 'proj/installations/'. The default version is 'python3.10.19'.

## Language Support
Includes 'proj.language_utils' for tool localization based on the 'TOOL_LANGUAGE' environment variable.
