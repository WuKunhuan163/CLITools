# logic/_/help/ — Hierarchical Help System

## Purpose

The `---help` eco command generates a DFS tree of all available commands by walking `logic/_/` directories and reading their `argparse.json` descriptors.

Unlike argparse's native `--help` (which only knows about a single parser), `---help` shows the **entire command surface** across all eco commands.

## How It Works

1. Walk `logic/_/` directories that contain `cli.py`
2. Read each directory's `argparse.json` for name, description, subcommands
3. Recursively process nested directories with their own `argparse.json`
4. Render as an indented DFS tree (or JSON with `--json`)

## argparse.json Schema

```json
{
  "$schema": "argparse/v1",
  "name": "command-name",
  "description": "Human-readable description",
  "subcommands": {
    "sub-name": {
      "description": "What this subcommand does",
      "args": [
        {"name": "positional_arg", "type": "positional", "help": "Description"},
        {"name": "--flag", "help": "Description", "action": "store_true"}
      ]
    }
  }
}
```

## Usage

```bash
TOOL ---help               # Full command tree
TOOL ---help audit         # Subtree for ---audit
TOOL ---help --json        # Machine-readable output
```

## Integration with Audit

`TOOL ---audit argparse` verifies that:
- Every `logic/_/<name>/cli.py` has a matching `argparse.json`
- argparse.json descriptions match the actual CLI behavior
- No orphaned argparse.json without a cli.py
