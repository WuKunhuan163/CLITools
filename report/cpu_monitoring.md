# CPU Monitoring Mechanism

## Implementation Detail
The CPU utilization monitoring is implemented using the `psutil` library. 

### Method
We use `psutil.cpu_percent(interval=0.1)` for instant checks at tool startup and `psutil.cpu_percent(interval=0.5)` for monitoring during the test wait stage.

### Performance Impact
- **Time Complexity**: The `interval` parameter determines the blocking time for sampling. At tool startup, we use a minimal `0.1s` interval, which is negligible for human interaction but provides a reasonably accurate snapshot of system load. During the test wait stage, the `0.5s` interval allows for more accurate sampling without spinning the CPU.
- **Space Complexity**: The memory footprint of `psutil` is minimal and constant. It reads from system files (like `/proc/stat` on Linux or via Mach system calls on macOS), which does not involve significant allocations.
- **Overhead**: The resource consumption of the monitoring itself is strictly negligible compared to the tasks being performed (like Python installations or GUI rendering).

## Usage
- **Tool Startup**: `ToolBase` checks the load and issues a `Warning` (yellow bold) if it exceeds the tool's `cpu_limit`.
- **Unit Testing**: `TOOL test` waits for the load to drop below the global `test_cpu_limit` (default 80%) before starting parallel test execution.
- **Configuration**:
    - Global: `TOOL config --test-cpu-limit 70.0`
    - Tool-specific: `TOOL_NAME config --cpu-limit 50.0`

