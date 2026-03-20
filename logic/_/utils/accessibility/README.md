# logic/accessibility

Keyboard accessibility: global paste+enter detection, modifier listeners, and shortcut settings.

## Contents

- **keyboard/monitor.py** - pynput-based global listener for paste+enter; accessibility permission checks
- **keyboard/settings.py** - Load/save keyboard shortcuts to `logic/config/keyboard.json`; GUI for capture-based key assignment

## Structure

```
accessibility/
  __init__.py
  keyboard/
    __init__.py
    monitor.py
    settings.py
```
