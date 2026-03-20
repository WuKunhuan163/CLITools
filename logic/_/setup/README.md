# Setup

Tool installation and uninstallation engine. Creates shortcuts, installs dependencies, runs setup.py.

## Purpose

`ToolEngine` orchestrates the full install lifecycle: registry validation, source fetch (git checkout), tool dependencies, pip dependencies, shortcut creation, and setup.py execution. Used by `TOOL install`, `tool --setup`, and `run_subtool_install`.

## Structure

| File | Responsibility |
|------|----------------|
| engine.py | ToolEngine class |

## Key Exports

- `ToolEngine` — install, uninstall, reinstall, create_shortcut
