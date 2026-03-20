# IDE Tool

AI IDE detection, configuration, and hook management for AITerminalTools.

## Features

- **IDE Detection**: Automatically detects Cursor, VS Code, and Windsurf
- **Rule Deployment**: Deploys `.mdc` rule templates to IDE configuration directories
- **Hook Management**: Manages IDE lifecycle hooks (sessionStart, postToolUse, stop, etc.)
- **Rule Generation**: Generates AI agent rule sets from the tool registry

## Usage

```bash
IDE status                    # Show detected IDEs and deployment state
IDE detect                    # Detect installed AI IDEs
IDE detect --json             # Detect as JSON
IDE deploy                    # Deploy rules and hooks
IDE deploy --force            # Force overwrite existing files
IDE rules                     # List deployed rules
IDE hooks                     # List registered hooks
IDE rule show                 # Show full AI agent rule set
IDE rule show --tool LLM      # Show rules for a specific tool
IDE rule inject               # Inject rule into .cursor/rules/
```

## Architecture

```
tool/IDE/
├── logic/
│   ├── detect.py                    # IDE detection (Cursor, VS Code, Windsurf)
│   ├── rule.py                      # Rule generation and injection
│   ├── instance/
│   │   └── cursor/                  # Cursor hook implementations
│   │       ├── brain_inject.py      # sessionStart: inject brain context
│   │       ├── brain_remind.py      # postToolUse: anti-fatigue USERINPUT reminder
│   │       ├── userinput_flag.py    # afterShellExecution: flag USERINPUT calls
│   │       ├── userinput_enforce.py # stop: enforce USERINPUT before turn end
│   │       └── file_search_fallback.py
│   └── setup/
│       ├── deploy.py                # Deployment logic
│       └── cursor/
│           ├── rules/*.mdc          # Rule templates
│           └── hooks/hooks.json     # Hook configuration template
├── interface/
│   └── main.py                      # Cross-tool API
└── main.py                          # CLI entry point
```

## Hook Lifecycle

```
User starts conversation
    │
    ▼
sessionStart → brain_inject.py → additional_context (brain + ecosystem)
    │
    ├─ postToolUse → brain_remind.py → tiered reminder
    ├─ afterFileEdit → brain_remind.py → same tiered system
    ├─ afterShellExecution (USERINPUT) → userinput_flag.py → sets flag
    │
    ▼
stop → userinput_enforce.py → checks flag → followup if missing
```

## Setup

The root `setup.py` calls `IDE deploy` during the "Deploying Cursor IDE config" stage. This is done automatically when running:

```bash
python setup.py
```

Manual deployment:

```bash
IDE deploy --force
```
