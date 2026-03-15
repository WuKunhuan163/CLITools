"""EXEC tool interface -- sandbox and command execution primitives.

Other tools import from here instead of reaching into EXEC internals.
"""

from tool.EXEC.logic.sandbox import (  # noqa: F401
    # Policy CRUD
    get_command_policy,
    set_command_policy,
    remove_command_policy,
    list_policies,
    reload_policies,
    # Path protection
    PROTECTED_PATTERNS,
    is_path_protected,
    filter_listing,
    resolve_path,
    # Command classification
    ALLOWED_COMMANDS,
    BLOCKED_COMMANDS,
    classify_command,
    get_blocked_hint,
    is_project_tool,
    # Interactive prompt
    prompt_permission,
    # Utilities
    get_project_root,
    MAX_OUTPUT_LENGTH,
)
