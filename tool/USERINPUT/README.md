# USERINPUT - User Input Tool for AI Agents

## Overview

USERINPUT is a specialized tool designed for AI agents (like Cursor AI) to request and receive user input during task execution. It provides a modern tkinter GUI interface with session identification capabilities, allowing AI agents to pause, wait for user feedback, and continue their work based on user instructions.

## Purpose

When an AI agent encounters uncertainty, needs clarification, or requires user approval, it can use USERINPUT to:
- Pause execution and wait for user input
- Display hints and contextual information to guide the user
- Support timeout mechanisms to prevent indefinite waiting
- Provide both CLI and GUI (Tkinter) interfaces for better user experience
- Handle multiline input gracefully

## Installation

USERINPUT is already installed in your project root at: `/Applications/AITerminalTools/USERINPUT`

## Usage

### Basic Usage

```bash
# Simple user input request
USERINPUT

# With timeout (seconds)
USERINPUT --timeout 60

# With custom ID for window identification
USERINPUT --id task_review

# Combined: timeout and custom ID
USERINPUT --timeout 120 --id code_approval
```

### Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--timeout SECONDS` | Set timeout in seconds | `USERINPUT --timeout 60` |
| `--id CUSTOM_ID` | Set custom ID for window title identification | `USERINPUT --id debug_session` |
| `--help` | Show help message | `USERINPUT --help` |

## Features

### 1. Timeout Support

USERINPUT can automatically timeout after a specified duration:

```bash
# Wait for 180 seconds (3 minutes)
USERINPUT --timeout 180
```

If the timeout is reached without user input, USERINPUT returns with a timeout message.

### 2. Custom ID Support

Provide custom identifiers to help users distinguish between multiple feedback windows:

```bash
# Different tasks with descriptive IDs
USERINPUT --id code_review --timeout 180
USERINPUT --id bug_report --timeout 120
USERINPUT --id final_approval --timeout 60
```

Window titles will display as: `project_name - Agent Mode [custom_id]`

### 3. Modern GUI Interface

USERINPUT displays a modern tkinter GUI window:
- Audio notification (plays bell sound on startup and periodic refocus)
- Clean, resizable interface with scrollable text area
- Displays project name, session info, and custom ID in window title
- Dynamic window sizing and automatic text area adjustment
- Countdown timer showing remaining time
- IMK message suppression for clean operation

### For AI Agents

1. **Always use timeout**: Prevent indefinite waiting
   ```bash
   USERINPUT --timeout 180  # 3 minutes is reasonable
   ```

2. **Provide clear hints**: Help users understand what you need
   ```bash
   USERINPUT --hint "Review the changes in git diff above and type 'continue' to proceed"
   ```

3. **Handle empty input**: Check if user provided input
   ```bash
   response=$(USERINPUT --timeout 60)
   if [ -z "$response" ]; then
       echo "No input provided, using default action"
   fi
   ```

4. **Repeat if needed**: If timeout occurs, call USERINPUT again
   ```bash
   USERINPUT --timeout 180 --hint "Still waiting for your feedback..."
   ```

5. **Show context before requesting input**: Display relevant information
   ```bash
   echo "=== Test Results ==="
   cat test_results.txt
   echo "==================="
   USERINPUT --hint "Are the test results satisfactory?"
   ```

### For Users

1. **Read the hint carefully**: Understand what the AI agent is asking for
2. **Provide clear, concise input**: Be specific in your instructions
3. **Use Ctrl+D to submit**: After typing your input, press Ctrl+D (not Enter)
4. **Watch for timeout**: Respond within the timeout period
5. **Use multiline input when needed**: Type multiple lines, then Ctrl+D

## Technical Details

### Architecture

- **Main Process**: Handles user input from stdin
- **Subprocess**: Displays Tkinter focus window
- **Audio Notification**: Plays bell sound (tkinter_bell.mp3)
- **Signal Handling**: Graceful SIGINT (Ctrl+C) handling

### Environment Detection

USERINPUT automatically detects:
- Project name (from git repository root)
- Current working directory

### File Locations

- Binary: `/Applications/AITerminalTools/USERINPUT`
- Python script: `/Applications/AITerminalTools/USERINPUT.py`
- Audio file: `/Applications/AITerminalTools/USERINPUT_PROJ/tkinter_bell.mp3`

## Examples

### Example 1: Simple Approval

```bash
#!/bin/bash
echo "About to delete old log files"
ls -lh logs/*.log
response=$(USERINPUT --timeout 60 --hint "Type 'yes' to confirm deletion")
if [ "$response" = "yes" ]; then
    rm logs/*.log
    echo "Log files deleted"
else
    echo "Operation cancelled"
fi
```

### Example 2: Iterative Task Execution

```bash
#!/bin/bash
task_count=0
while true; do
    task_count=$((task_count + 1))
    echo "=== Task $task_count completed ==="
    
    next_task=$(USERINPUT --timeout 300 --hint "What should I do next? (type 'exit' to finish)")
    
    if [ "$next_task" = "exit" ]; then
        echo "All tasks completed"
        break
    fi
    
    echo "Working on: $next_task"
    # Process the task...
done
```

### Example 3: Multi-option Selection

```bash
#!/bin/bash
echo "Select deployment environment:"
echo "1. Development"
echo "2. Staging"
echo "3. Production"

choice=$(USERINPUT --timeout 60 --hint "Enter number (1-3)")

case $choice in
    1) echo "Deploying to Development..." ;;
    2) echo "Deploying to Staging..." ;;
    3) echo "Deploying to Production..." ;;
    *) echo "Invalid choice" ;;
esac
```

## Troubleshooting

### Issue: Focus window doesn't appear

**Solution**: Check if Tkinter is installed:
```bash
python3 -c "import tkinter"
```

If not installed, run:
```bash
# macOS
brew install python-tk

# Ubuntu/Debian
sudo apt-get install python3-tk
```

### Issue: Audio notification doesn't play

**Solution**: Ensure audio file exists:
```bash
ls -l ./USERINPUT_PROJ/tkinter_bell.mp3
```

You can disable audio by modifying the code or use `--no-focus` to disable the entire focus window.

### Issue: Timeout too short

**Solution**: Increase timeout value:
```bash
USERINPUT --timeout 300  # 5 minutes
```

### Issue: Input not captured

**Solution**: Make sure to press `Ctrl+D` (EOF) after typing your input, not just Enter.

## See Also

- **BACKGROUND_CMD**: Background command execution
- **AI_TOOL**: AI tool registry and management

## License

Part of the AITerminalTools suite.