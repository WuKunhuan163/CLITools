# GCS MCP: Create Remote Notebook

## Purpose
Create `.root.ipynb` in the Env folder on Google Drive. Uses CDP + gapi.client when debug Chrome is available (preferred), or browser MCP workflow as fallback.

## Prerequisites
- GCS setup tutorial completed (Steps 1-5)
- Debug Chrome running with CDP (via `GCS --mcp boot`)

## Usage

### Method 1: CDP (Preferred)
When debug Chrome is running with a Colab tab:

```bash
GCS --mcp-create colab @ --name .root.ipynb
```

This uses `gapi.client.request()` to create the notebook directly via the Drive API, using the user's existing auth session in the Colab tab. The notebook ID is automatically saved to GCS config.

### Method 2: Browser MCP Workflow (Fallback)
When CDP is not available:

```bash
GCS --mcp-create colab @ --name .root.ipynb --json
```

Returns a JSON workflow with browser MCP steps for the agent to execute (navigate Drive, click New, select Colaboratory, etc.).

## Related Commands

```bash
GCS --mcp-list @          # List files in env folder
GCS --mcp-list ~          # List files in root folder
GCS --mcp-delete FILE_ID  # Delete a file by ID
GCS --mcp-create TYPE FOLDER [--name NAME]  # Create any Google file type
```

Supported file types: `colab`, `doc`, `sheet`, `slide`, `form`, `drawing`, `script`, `site`, `folder`

## Idempotency
- If `.root.ipynb` exists with size > 0, no action is taken
- If it exists with size = 0 (corrupted), it should be deleted and recreated
- If it doesn't exist, the creation workflow executes
