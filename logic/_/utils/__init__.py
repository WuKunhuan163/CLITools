# Public API re-exports for `from logic._.utils import X`.
# Submodules: cleanup, display, fuzzy, logging, preflight, progress, resolve, system, timezone, turing

from logic._.utils.cleanup import cleanup_old_files, cleanup_project_patterns
from logic._.utils.display import (
    set_rtl_mode, get_rtl_mode,
    get_display_width, print_terminal_width_separator,
    truncate_to_display_width, get_rate_color,
    format_seconds, format_table, save_list_report,
    print_success_status,
)
from logic._.utils.logging import SessionLogger, log_debug
from logic._.utils.progress import retry, calculate_eta, run_with_progress
from logic._.utils.resolve import find_project_root, setup_paths, get_tool_module_path
from logic._.utils.system import (
    get_system_tag, regularize_version_name, extract_resource,
    print_missing_tool_error, print_python_not_found_error,
    get_python_tool_exec, get_python_exec,
    check_and_reexecute_with_python,
    get_logic_dir, get_module_relative_path,
    register_path, get_tool_bin_path,
    get_cpu_percent, get_variable_from_file,
)
from logic._.utils.timezone import get_current_timezone, resolve_timezone
from logic._.utils.fuzzy import suggest_commands, suggest_with_scores, format_suggestion
from logic._.utils.preflight import preflight, check_command_exists, check_path_exists, check_port_available
