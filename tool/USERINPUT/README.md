# USERINPUT Tool

CAPTURES multi-line user feedback via a Tkinter GUI.

## Features
- **Time-Limited**: Defaults to 180s timeout.
- **Partial Capture**: Returns current text even if timeout or terminated.
- **Robust 'Stop'**: Use `USERINPUT stop` to gracefully close active windows.
- **AI Instruction**: Automatically generates guidance for AI agents.

## Usage
```bash
USERINPUT --hint "Please review this plan" --timeout 300
```

## Management
- **Stop All**: `USERINPUT stop`
- **Stop Specific**: `USERINPUT stop <PID>`
- **Config**: `USERINPUT config --focus-interval 90`

## Implementation
This tool inherits from the unified [GUI Architecture](../../report/gui_architecture.md) blueprint, ensuring consistent UI styling and signal handling across the ecosystem.
