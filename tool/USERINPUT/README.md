# USERINPUT Tool

CAPTURES multi-line user feedback via a Tkinter GUI.

## Features
- **Time-Limited**: Defaults to 300s timeout with automatic refocus.
- **Partial Capture**: Returns current text even if timeout or terminated.
- **Robust 'Stop'**: Use `USERINPUT stop` to gracefully close active windows.
- **AI Instruction**: Automatically generates guidance for AI agents.
- **Auto-Commit**: Saves your work progress before waiting for user feedback.
- **Sandbox Fallback**: Switches to file-based input (`data/USERINPUT/input/*.txt`) if GUI cannot launch.

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
