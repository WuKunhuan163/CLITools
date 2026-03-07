# FILEDIALOG Tool

GUI-based file and directory selection dialog.

## Features

- **Multi-selection**: Support for selecting multiple files using Shift or Ctrl/Cmd.
- **Navigation**: Clickable breadcrumbs and history buttons (←/→).
- **Sorting**: Clickable column headers for name, size, and type.
- **Sandbox Fallback**: If running in a restricted terminal (e.g. Cursor, Docker), it automatically falls back to a file-based selection interface.
- **Symmetry**: Shared infrastructure with `USERINPUT` for consistent user experience.

## Usage

### Basic Selection
```bash
FILEDIALOG
```

### Multiple File Selection
```bash
FILEDIALOG --multiple
```

### Directory Only Selection
```bash
FILEDIALOG --directory
```

### Custom Title and Start Directory
```bash
FILEDIALOG --title "Select Photos" --dir ~/Pictures
```

