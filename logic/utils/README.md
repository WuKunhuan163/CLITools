# logic/utils

Shared utilities: display, logging, progress, system detection, cleanup, and timezone.

## Contents

- **display.py** - RTL mode, `get_display_width`, `truncate_to_display_width`, `print_terminal_width_separator`, `get_rate_color`, `format_seconds`, `format_table`, `save_list_report`, `print_success_status`
- **logging.py** - `SessionLogger`, `log_debug`
- **progress.py** - `retry`, `calculate_eta`, `run_with_progress`
- **system.py** - `get_system_tag`, `get_logic_dir`, `find_project_root`, `get_cpu_percent`, `get_variable_from_file`, `get_tool_bin_path`, Python exec helpers
- **cleanup.py** - `cleanup_old_files`, `cleanup_project_patterns`
- **timezone.py** - `get_current_timezone`, `resolve_timezone`

## Structure

```
utils/
  __init__.py
  display.py
  logging.py
  progress.py
  system.py
  cleanup.py
  timezone.py
```
