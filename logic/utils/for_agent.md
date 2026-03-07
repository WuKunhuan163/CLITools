# logic/utils - Agent Reference

> **Import convention**: Tools should import from `interface.utils` (the facade), not directly from `logic.utils`. See `interface/for_agent.md`.

## Key Interfaces

### display.py
- `get_display_width(text)` - East Asian width, ANSI stripped, RTL markers ignored
- `truncate_to_display_width(text, max_width)` - CJK-aware
- `get_rate_color(rate_str)` - <60% red, 60-90% yellow, 90-100% blue, 100% green
- `format_table(headers, rows, max_width, save_dir)` - Box-drawing table; truncates and saves full to `data/table/{save_dir}/`
- `print_success_status(action_msg)` - Bold green "Successfully" + message
- `set_rtl_mode`, `get_rtl_mode` - Global RTL for formatting

### logging.py
- `SessionLogger(log_dir, limit, prefix)` - `write(message, extra, include_stack)`, `write_exception(error, context)`, `path`
- `log_debug(msg)` - Writes to `/tmp/ait_debug.log`

### progress.py
- `retry(max_attempts, backoff, retryable_exceptions, retryable_status_codes)` - Decorator
- `calculate_eta(current, total, elapsed_time)` - Returns (elapsed_str, remaining_str)
- `run_with_progress(cmd, prefix, worker_id, manager, interval)` - Parses stderr for %; supports curl, git push

### system.py
- `find_project_root(start_path)` - Looks for bin/TOOL + tool.json or tool.json + logic + tool
- `get_logic_dir(base_dir)` - Returns base_dir / "logic"
- `get_cpu_percent(interval)` - psutil
- `get_variable_from_file(file_path, var_name, default)` - AST extraction
- `get_tool_bin_path(project_root, tool_name)` - bin/shortcut/shortcut or bin/shortcut
- `check_and_reexecute_with_python(tool_name, version)` - Re-exec with PYTHON tool if needed

### cleanup.py
- `cleanup_old_files(target_dir, pattern, limit, batch_size)` - Deletes oldest when exceeded
- `cleanup_project_patterns(root_dir, patterns)` - Recursive delete .DS_Store, __pycache__

### timezone.py
- `get_current_timezone()` - IP-based or config
- `resolve_timezone(tz_input)` - Returns (tz_object, display_name); supports AUTO, UTC+X, city names

## Usage Patterns

1. **Project root**: `find_project_root(Path(__file__))` from any module
2. **Tables**: `format_table(headers, rows, max_width=width)` for terminal; full saved if truncated
3. **Progress**: Use `run_with_progress` with MultiLineManager for subprocess progress

## Gotchas

- `get_display_width` handles Arabic ligatures (width -= 1 for lam-alef)
- `run_with_progress` sets LC_ALL=C; stderr only
- `find_project_root` avoids returning when parent.name == "tool" (nested tool dir)
