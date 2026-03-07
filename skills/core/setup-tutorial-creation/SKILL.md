---
name: setup-tutorial-creation
description: Creating interactive setup wizards with the TutorialWindow system. Multi-step GUI guides for tool configuration.
---

# Setup Tutorial Creation

## Overview

The `TutorialWindow` system provides multi-step GUI wizards for tool setup, using Tkinter.

## Creating a Tutorial

```python
from interface.gui import TutorialWindow

def create_setup_tutorial():
    steps = [
        {
            "title": "Welcome",
            "content": "This wizard will help you configure MY_TOOL.",
            "type": "info",
        },
        {
            "title": "API Key",
            "content": "Enter your API key below:",
            "type": "input",
            "key": "api_key",
            "placeholder": "sk-...",
        },
        {
            "title": "Select Region",
            "content": "Choose your preferred region:",
            "type": "select",
            "key": "region",
            "options": ["us-east", "us-west", "eu-west", "ap-east"],
        },
        {
            "title": "Complete",
            "content": "Setup is complete. Your settings have been saved.",
            "type": "info",
        },
    ]
    tutorial = TutorialWindow(title="MY_TOOL Setup", steps=steps)
    return tutorial.run()  # Returns dict of collected values
```

## Step Types

| Type | Description | Required Fields |
|------|-------------|-----------------|
| `info` | Display-only text | `title`, `content` |
| `input` | Text input field | `title`, `content`, `key`, `placeholder` |
| `select` | Dropdown selection | `title`, `content`, `key`, `options` |
| `checkbox` | Boolean toggle | `title`, `content`, `key` |
| `file` | File picker | `title`, `content`, `key`, `file_types` |

## Integration with setup.py

```python
class MySetup(ToolEngine):
    def install(self):
        results = create_setup_tutorial()
        if results:
            self.save_config(results)
            print(f"  Configuration saved.")
        else:
            print(f"  Setup cancelled.")
```

## Guidelines

1. Keep tutorials concise (3-6 steps max)
2. Provide sensible defaults for optional fields
3. Validate input before advancing to next step
4. Allow cancellation at any step
5. Save configuration atomically (write temp file, then rename)
