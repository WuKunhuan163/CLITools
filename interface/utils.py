"""Utility interface for tools.

Provides reusable utility functions: preflight checks, retry decorators,
file cleanup/rotation, fuzzy matching, display helpers, timezone, and
system introspection.
"""
from logic.utils.preflight import (
    preflight,
    check_command_exists,
    check_path_exists,
    check_port_available,
)
from logic.utils.progress import retry, calculate_eta, run_with_progress
from logic.utils.cleanup import cleanup_old_files, cleanup_project_patterns
from logic.utils.fuzzy import suggest_commands, suggest_with_scores, format_suggestion
from logic.utils.display import (
    get_display_width,
    truncate_to_display_width,
    format_seconds,
    format_table,
    print_success_status,
)
from logic.utils.logging import SessionLogger, log_debug
from logic.utils.timezone import get_current_timezone, resolve_timezone
from logic.utils.system import (
    find_project_root,
    get_tool_module_path,
    get_python_exec,
    get_system_tag,
    regularize_version_name,
    extract_resource,
    register_path,
    get_logic_dir,
    get_tool_bin_path,
)
from logic.utils.platform import (
    current_platform,
    find_chrome_binary,
    launch_chrome_cdp,
    cleanup_chrome,
    register_handler,
    dispatch,
)
from logic.utils.display import save_list_report, set_rtl_mode
from logic.utils.exchange import (
    get_rates, to_usd, get_rate, convert,
    get_precision, get_symbol, get_currency_name, format_price, list_currencies,
)

__all__ = [
    # Preflight checks
    "preflight",
    "check_command_exists",
    "check_path_exists",
    "check_port_available",
    # Retry/progress
    "retry",
    "calculate_eta",
    "run_with_progress",
    # Cleanup/rotation
    "cleanup_old_files",
    "cleanup_project_patterns",
    # Fuzzy matching
    "suggest_commands",
    "suggest_with_scores",
    "format_suggestion",
    # Display
    "get_display_width",
    "truncate_to_display_width",
    "format_seconds",
    "format_table",
    "print_success_status",
    # Logging
    "SessionLogger",
    "log_debug",
    # Timezone
    "get_current_timezone",
    "resolve_timezone",
    # System
    "find_project_root",
    "get_tool_module_path",
    "get_python_exec",
    "get_system_tag",
    "regularize_version_name",
    "extract_resource",
    "register_path",
    "get_logic_dir",
    "get_tool_bin_path",
    "save_list_report",
    "set_rtl_mode",
    # Exchange rates
    "get_rates",
    "to_usd",
    "get_rate",
    "convert",
    "get_precision",
    "get_symbol",
    "get_currency_name",
    "format_price",
    "list_currencies",
]
