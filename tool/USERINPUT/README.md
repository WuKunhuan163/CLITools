# USERINPUT Tool

Captures multi-line user feedback via a Tkinter GUI with queue-based task management.

## Features

- **Time-Limited**: Defaults to 300s timeout with automatic refocus.
- **Partial Capture**: Returns current text even on timeout or termination.
- **Robust Stop**: Use `USERINPUT --gui-stop` to gracefully close active windows.
- **AI Instruction**: Automatically generates guidance for AI agents.
- **Auto-Commit**: Saves work progress before waiting for user feedback.
- **Sandbox Fallback**: Switches to file-based input if GUI cannot launch.
- **Queue System**: Pre-queue prompts for agents to claim when the user is away.
- **Enquiry Mode**: Bypass the queue to get real-time feedback from the user.

## Usage

```bash
USERINPUT --hint "Please review this plan" --timeout 300
```

## Queue System

The queue mechanism mimics Cursor's queued prompts, allowing users to prepare tasks for agents to claim later.

```bash
# Add a prompt to the queue (opens GUI, saves input to queue)
USERINPUT --queue

# Add a prompt to the queue directly (no GUI)
USERINPUT --queue --add "Build the login page"

# List all queued prompts
USERINPUT --queue --list

# Delete a queued prompt by index
USERINPUT --queue --delete 2

# Manage queue via GUI
USERINPUT --queue --gui

# Reorder queue items (0-indexed)
USERINPUT --queue --move-up 2
USERINPUT --queue --move-down 0
USERINPUT --queue --move-to-top 3
USERINPUT --queue --move-to-bottom 1
```

When `USERINPUT` is called normally (without `--queue`), it automatically claims the first queued prompt instead of opening the GUI. The status changes from "Successfully received" to "Successfully received from queue".

### Enquiry Mode

Use `--enquiry` to bypass the queue and request real-time user feedback. This is for situations where the agent needs to ask the user a question mid-task without being redirected by a queued prompt.

```bash
USERINPUT --enquiry --hint "Should I proceed with approach A or B?"
```

## System Prompt Management

```bash
# List current system prompts
USERINPUT config --list

# Add / remove prompts
USERINPUT config --add "New instruction"
USERINPUT config --delete 3

# Reorder prompts
USERINPUT config --move-up 2
USERINPUT config --move-to-top 5

# Manage via GUI
USERINPUT config --gui
```

## Remote Control

- **Stop All**: `USERINPUT --gui-stop`
- **Stop Specific**: `USERINPUT --gui-stop <PID>`
- **Config**: `USERINPUT config --focus-interval 90`

## Implementation

This tool inherits from the unified [GUI Architecture](../../report/gui_architecture.md) blueprint. Queue management uses the `editable_list` blueprint which inherits from the `bottom_bar` blueprint.
