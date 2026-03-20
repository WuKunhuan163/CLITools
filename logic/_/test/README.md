# logic/test

Test runner and management for tools and root project.

## Contents

- **manager.py** - Entry point `test_tool_with_args`, `run_installation_test`; CPU wait, branch handling, persistence
- **runner.py** - `TestRunner` class: discovers `test/test_*.py`, runs parallel/sequential, uses TuringWorker for display

## Structure

```
test/
  manager.py
  runner.py
```
