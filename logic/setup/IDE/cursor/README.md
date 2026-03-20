# Cursor IDE Setup Templates

Templates for Cursor IDE configuration. Auto-deployed by `setup.py` when it detects a Cursor IDE environment.

## Structure

```
logic/setup/cursor/
├── rules/              # Cursor rule templates (.mdc files)
│   ├── agent-brain.mdc       # Brain read/write management
│   └── userinput-timeout.mdc # USERINPUT long wait handling
├── hooks/              # Cursor hooks configuration
│   └── hooks.json      # hooks.json template
└── README.md
```

## Detection

Cursor IDE is detected by checking:
1. `CURSOR_VERSION` environment variable (set when running inside Cursor terminal)
2. Existence of `~/.cursor/` directory
3. Existence of `.cursor/` in project root

## Deployment

The `setup_cursor_ide_action()` stage in `setup.py`:
1. Copies rule templates to `.cursor/rules/`
2. Copies hooks.json to `.cursor/hooks.json`
3. Only overwrites if source is newer than destination
4. Skips if Cursor IDE is not detected

## Adding New Rules

1. Create the `.mdc` file in `logic/setup/cursor/rules/`
2. The next `python setup.py` run will deploy it to `.cursor/rules/`
