# TAVILY Logic — Technical Reference

## Tutorial System

### setup_guide/ (2 steps)
- `step_01/`: Prompt user for Tavily API key
- `step_02/`: Validate key and save to config

### tutorial_cmd.py
Launches the setup wizard via `TutorialWindow`. Uses `interface.lang.get_translation` for i18n.

## Gotchas

1. **Minimal logic layer**: Most Tavily functionality is in `main.py` directly, not in `logic/`. The logic layer only handles the setup tutorial.
