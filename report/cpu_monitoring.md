# CPU Load Monitoring Report

## Mechanism
The CPU load monitoring is implemented using the `psutil` library, specifically the `psutil.cpu_percent(interval=...)` function.

- **Initialization**: `ToolBase` and `TOOL test` check the current system-wide CPU utilization.
- **Per-Test Limits**: Individual unit tests can define an `EXPECTED_CPU_LIMIT` (e.g., `40.0` for 40%) at the top of the file. The `TestRunner` uses `ast` to parse this value without executing the file.
- **Wait Logic**: If the current CPU load exceeds the configured limit, the system enters a "Waiting for CPU load" stage using the `ProgressTuringMachine`. It polls the CPU load every 0.5-1.0 seconds until it drops below the limit or a timeout is reached.
- **Global Config**: Global defaults are managed via `TOOL config --test-cpu-limit <float>` and `--test-cpu-timeout <int>`.

## Performance Impact
- **Time Overhead**: `psutil.cpu_percent(interval=0.1)` takes approximately 100ms. In the `TestRunner` loop, we use `interval=0.5`. This overhead is negligible compared to the total duration of most unit tests.
- **Space Overhead**: `psutil` is a lightweight C-extension with minimal memory footprint. The `ast` parsing for `EXPECTED_CPU_LIMIT` is extremely fast and only happens once per test file discovery.
- **Overall**: The performance impact is negligible and can be considered "zero-cost" in the context of terminal tool execution and testing.

## Conclusion
The mechanism provides a robust way to prevent flaky test results on overloaded systems with minimal impact on performance.
