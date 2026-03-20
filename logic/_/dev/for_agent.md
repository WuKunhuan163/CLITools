# logic/dev - Agent Reference

## Key Interfaces

### commands.py
- Re-exports all from `logic.tool.dev.commands`
- Canonical: `logic.tool.dev.commands`
- Provides `dev_sync`, `align_branches` and related dev workflow commands

## Usage

Import from `logic.dev.commands` for backward compatibility; implementation in `logic.tool.dev.commands` and `logic.git.manager`.
