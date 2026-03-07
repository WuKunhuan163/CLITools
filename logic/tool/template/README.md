# {name} Tool

{description}

## Overview

This tool is part of the **AITerminalTools** ecosystem. It is designed to be easily managed, tested, and localized.

## Key Features

- **Standardized Setup**: Uses a `setup.py` script for automatic environment configuration and dependency management.
- **Turing Progress Display**: Leverages the shared `logic/turing` module for rich, multi-line terminal progress updates.
- **Localization**: All user-facing strings are stored in `logic/translation/` for easy translation.
- **Unit Testing**: Pre-configured test suite in the `test/` directory.

## Development Guidelines

### 1. Localization
Never hardcode user-facing strings. Use the `_()` helper:
```python
from logic.lang.utils import get_translation
# ...
print(_("my_key", "Default English String"))
```
Add your translations to `logic/translation/zh.json`, etc.

### 2. Shared Utilities
Check the root `logic/` directory before implementing common logic. It contains:
- `logic/utils.py`: Terminal formatting, platform detection, progress wrappers.
- `logic/git.py`: Standardized Git operations with progress display.
- `logic/turing/`: Advanced progress state machine.
- `logic/worker.py`: Parallel task worker system.

### 3. Git Integration
- **Git LFS**: Large assets are automatically tracked via `.gitattributes`.
- **Auto-Push**: The ecosystem can be configured to auto-push your work periodically to prevent loss.

### 4. Testing
Run tests using the central manager:
```bash
TOOL test {name}
```
Ensure your tests do not hardcode absolute paths. Use relative paths or shared configuration helpers.

## Repository Structure

- `main.py`: Main entry point.
- `setup.py`: Environment setup and dependency check.
- `logic/`: Tool-specific logic and translations.
- `test/`: Unit tests.
- `tool.json`: Metadata and dependencies.


