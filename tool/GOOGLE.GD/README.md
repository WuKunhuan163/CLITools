# GOOGLE.GD

> **ToS Compliance — DISABLED**: This tool performs Google Drive operations
> via Chrome DevTools Protocol (CDP) browser automation. Automated interaction
> with Google Drive's web UI may violate Google's Terms of Service.
> All CDP-based functionality has been disabled. Use the Google Drive API
> via service account credentials (see GOOGLE.GDS) for programmatic access.

Google Drive file operations via Chrome DevTools Protocol (CDP) (disabled).

## Commands

```bash
GOOGLE.GD list <folder_id>           # List files in a folder
GOOGLE.GD create <name> --type colab --folder <id>  # Create a file
GOOGLE.GD delete <file_id>           # Delete a file
GOOGLE.GD about                      # Show user and quota info
```

## Interface

Other tools can import Drive functions:

```python
from tool.GOOGLE.logic.chrome.drive import (
    list_drive_files, create_drive_file, delete_drive_file,
    create_notebook, get_drive_about, DRIVE_MIME_TYPES,
)
```

## Dependencies

- **GOOGLE**: Provides core CDP session management and Chrome automation.
- **PYTHON**: Managed Python runtime.
