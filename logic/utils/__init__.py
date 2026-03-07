# Backward-compatible re-exports: `from logic.utils import X` still works.
# Submodules: cleanup, display, fuzzy, logging, preflight, progress, system, timezone

from logic.utils.cleanup import cleanup_old_files, cleanup_project_patterns
from logic.utils.display import (
    set_rtl_mode, get_rtl_mode,
    get_display_width, print_terminal_width_separator,
    truncate_to_display_width, get_rate_color,
    format_seconds, format_table, save_list_report,
    print_success_status,
)
from logic.utils.logging import SessionLogger, log_debug
from logic.utils.progress import retry, calculate_eta, run_with_progress
from logic.utils.system import (
    get_system_tag, regularize_version_name, extract_resource,
    print_missing_tool_error, print_python_not_found_error,
    get_python_tool_exec, get_python_exec,
    check_and_reexecute_with_python,
    get_logic_dir, find_project_root,
    get_tool_module_path, get_module_relative_path,
    register_path, get_tool_bin_path,
    get_cpu_percent, get_variable_from_file,
)
from logic.utils.timezone import get_current_timezone, resolve_timezone
from logic.utils.fuzzy import suggest_commands, suggest_with_scores, format_suggestion
from logic.utils.preflight import preflight, check_command_exists, check_path_exists, check_port_available
