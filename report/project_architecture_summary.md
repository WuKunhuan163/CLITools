# AITerminalTools Architecture Summary

## Overview

AITerminalTools is a modular terminal tool framework that provides standardized lifecycle management, GUI integration, multi-language localization, and isolated Python runtimes for a collection of developer-facing tools. It is designed to be operated both by human developers and by AI agents (particularly Cursor IDE agents).

## Core Architecture

### Directory Layout

```
/Applications/AITerminalTools/
├── main.py                 # Root CLI dispatcher (TOOL command)
├── setup.py                # Initial deployment (creates bin/TOOL, PATH setup)
├── tool.json               # Global tool registry
├── logic/                  # Shared framework code
│   ├── tool/               # ToolBase, ToolEngine, lifecycle
│   ├── turing/             # Progress display (ProgressTuringMachine, TuringStage)
│   ├── git/                # Git operations, branch sync, persistence
│   ├── dev/                # Developer commands (sync, create, audit)
│   ├── test/               # Test runner and manager
│   ├── lang/               # Localization (translation lookup, audit)
│   ├── gui/                # GUI blueprints and subprocess management
│   ├── config/             # Global config, color management
│   └── utils.py            # Path resolution, logging, utilities
├── tool/                   # All active tools
│   ├── <TOOL_NAME>/
│   │   ├── main.py         # Entry point
│   │   ├── setup.py        # Post-install setup
│   │   ├── tool.json       # Tool metadata and dependencies
│   │   ├── logic/          # Tool-specific logic
│   │   ├── test/           # Unit tests (test_XX_name.py)
│   │   └── data/           # Runtime data, config, logs
├── bin/                    # Managed bootstrap shortcuts
├── data/                   # Global config and logs
├── resource/               # Binary assets (tool branch only)
│   ├── tool/               # Active resources
│   └── archived/           # Archived tools (TOOL install fallback)
├── report/                 # Documentation reports
└── tmp/                    # Temporary/scratch files
```

### Symmetrical Design

The framework uses a symmetrical `logic/` pattern: the root `logic/` provides shared utilities, while each tool has its own `logic/` directory for tool-specific code. Python's `sys.path` is managed so that `from logic...` always resolves to the root framework.

## Key Components

### ToolBase (`logic/tool/base.py`)
The base class for all tools. Provides:
- Command-line handling with automatic subcommand routing
- CPU load monitoring and warnings
- Session logging
- Config management
- System command fallback for wrapper tools (e.g., GIT wraps `/usr/bin/git`)

### ToolEngine (`logic/tool/setup/engine.py`)
Manages the full tool installation lifecycle:
1. Registry validation (tool.json)
2. Source fetching (branch checkout → archived fallback)
3. Dependency resolution (recursive tool deps + pip deps)
4. Shortcut creation (bin/ managed bootstrap)
5. Post-install setup (setup.py)

### ProgressTuringMachine (`logic/turing/models/progress.py`)
The progress display system using sequential erasable terminal lines. Each stage transitions through active → success/fail states with colored output. Supports ephemeral mode, stealth stages, and keyboard suppression.

### Branch Strategy
- **dev**: Active development (resource/ gitignored)
- **tool**: Staging (includes resource/)
- **main**: Clean production framework (no tools)
- **test**: Testing mirror of tool branch

Synchronized via `TOOL dev sync` which propagates dev → tool → main → test.

## Registered Tools (18)

| Tool | Purpose |
|------|---------|
| PYTHON | Standalone Python 3.11 runtime |
| USERINPUT | Tkinter GUI for user feedback |
| BACKGROUND | Background process management |
| FILEDIALOG | File/directory selection GUI |
| TEX | LaTeX compilation and templates |
| SEARCH | Web and academic search |
| READ | File reading/processing |
| DRAW | Image drawing and annotation |
| GIT | Git wrapper with progress |
| FONT | Font management |
| FITZ | PDF processing |
| iCloud | iCloud ecosystem parent |
| iCloud.iCloudPD | Parallel iCloud photo downloader |
| GOOGLE | Google ecosystem parent |
| GOOGLE.GDS | Google Colab/Drive remote controller |
| SKILLS | Agent skill management |
| TAVILY | AI-optimized web search |
| DUMMY | Template/reference tool |

## Testing Framework

Tests follow the `test_XX_name.py` naming convention. `TOOL test <NAME>` switches to the test branch, runs parallel test discovery, monitors CPU load, and restores the original branch afterward. Per-test `EXPECTED_TIMEOUT` and `EXPECTED_CPU_LIMIT` settings are supported.

## Localization

Multi-language support via `_()` translation helper. English strings serve as defaults in code; translations are stored in `logic/translation/<lang>.json`. The `TOOL lang audit` command checks coverage.

---
*Generated: 2026-02-28*
