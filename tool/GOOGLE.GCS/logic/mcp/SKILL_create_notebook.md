# GCS MCP: Colab Tab Management

## Overview
GCS no longer requires a dedicated `.root.ipynb` notebook. Any open Google Colab tab (including the default "Welcome to Colab" page) is sufficient for remote execution.

## Boot
```bash
GCS --mcp boot
```
This launches debug Chrome (if not already running) and opens a Colab tab. If a Colab tab is already open, it is reused.

## How It Works
- `GCS --mcp boot` ensures a Colab tab is accessible via Chrome DevTools Protocol (CDP).
- `GCS <command> --mcp` finds the open Colab tab, creates a fresh code cell, injects the command, and executes it.
- No specific notebook file ID is stored or required.

## Related Commands

```bash
GCS --mcp-list @          # List files in env folder
GCS --mcp-list ~          # List files in root folder
GCS --mcp-create TYPE FOLDER [--name NAME]  # Create any Google file type
GCS --mcp-delete FILE_ID  # Delete a file by ID
```

Supported file types: `colab`, `doc`, `sheet`, `slide`, `form`, `drawing`, `script`, `site`, `folder`
