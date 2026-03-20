# logic/test - Agent Reference

## Key Interfaces

### manager.py
- `test_tool_with_args(args, project_root, translation_func)` - Main entry: CPU wait stage, branch save/restore, persistence save/restore, runs TestRunner
- `run_installation_test(tool_name, project_root, stay_on_test, translation_func)` - Syncs branches, checks out test, runs `TOOL install`, verifies bin shortcut and --help

### runner.py
- `TestRunner(tool_name, project_root)` - tool_name "root" = project root
- `list_tests()` - Prints test files sorted by numeric prefix
- `run_tests(start_id, end_id, max_concurrent, timeout, quiet_if_no_tests)` - Runs tests; parallel by default, sequential if `SEQUENTIAL = True` in file
- `_get_test_files()` - `test/test_*.py` sorted by `test_XX_name` prefix
- `_cleanup_resources(test_pids)` - Terminates GUI instances and leftover test processes (psutil)

## Test File Conventions

- `test_*.py` in `tool_dir/test/` or `project_root/test/`
- `SEQUENTIAL = True` at top - run one at a time
- `EXPECTED_TIMEOUT = N` - Override default 60s
- `EXPECTED_CPU_LIMIT = N` - Per-test CPU threshold (default from settings)
- Results saved to `data/_/test/result/`

## Usage Patterns

1. Tests run on current branch; manager saves/restores branch and persistence
2. Parallel tests use `TuringWorker` + `MultiLineManager` for live status
3. PYTHON dependency: uses `get_python_exec()` from PYTHON tool if present

## Gotchas

- `run_installation_test` switches to test branch; use `stay_on_test=False` to return
- `_cleanup_resources` targets GUI PIDs from `data/run/instances/gui_*.json` whose parent is a test PID
- CPU wait uses `get_global_config("test_cpu_limit")` and `test_cpu_timeout`
