#!/usr/bin/env python3
"""
Google Drive Modules
重构后的模块导入 - 委托模式版本
"""

# 导入所有模块的函数（保持向后兼容）
# core_utils已合并到remote_commands中
from .drive_process_manager import *
from .sync_config_manager import *
from .remote_shell_manager import *
from .drive_api_service import *
from .shell_commands import *
from .hf_credentials_manager import *
from .utils import is_run_environment, write_to_json_output
from .delegate_managers import (
    CoreUtils,
    DriveProcessManager,
    SyncConfigManager,
    SetupWizard,
    RemoteShellManager,
    DriveApiService,
    ShellCommands,
    HfCredentialsManager
)

# 导入原有的Google Drive Shell系统类
try:
    from .shell_management import ShellManagement
    from .file_operations import FileOperations
    from .cache_manager import CacheManager
    from .command_executor import CommandExecutor
    from .path_resolver import PathResolver
    from .sync_manager import SyncManager
    from .file_utils import FileUtils
    from .validation import Validation
    from .verification import Verification
    from .config_loader import (
        BG_STATUS_FILE_TEMPLATE,
        BG_SCRIPT_FILE_TEMPLATE,
        BG_LOG_FILE_TEMPLATE,
        BG_RESULT_FILE_TEMPLATE,
        get_bg_status_file,
        get_bg_script_file,
        get_bg_log_file,
        get_bg_result_file
    )
except ImportError as e:
    print(f"Warning: Import Google Drive Shell system class failed: {e}")

# 导出所有函数和管理器类
__all__ = [
    # Google Drive Shell系统类
    "ShellManagement",
    "FileOperations", 
    "CacheManager",
    "CommandExecutor",
    "CommandGenerator", 
    "FileValidator",
    "ResultProcessor",
    "PathResolver",
    "SyncManager",
    "FileUtils",
    "Validation",
    "Verification",
    # 委托模式管理器类
    "CoreUtils",
    "DriveProcessManager", 
    "SyncConfigManager",
    "SetupWizard",
    "RemoteShellManager",
    "DriveApiService",
    "ShellCommands",
    "HfCredentialsManager",
    # 函数（向后兼容）
    "checkout_shell",
    "console_setup_interactive",
    "console_setup_step2",
    "console_setup_step3",
    "console_setup_step4",
    "console_setup_step5",
    "console_setup_step6",
    "console_setup_step7",
    "copy_to_clipboard",
    "create_shell",
    "enter_shell_mode",
    "exit_shell",
    "extract_folder_id_from_url",
    "generate_shell_id",
    "get_current_shell",
    "get_google_drive_processes",
    "get_google_drive_status",
    "get_local_hf_token",
    "get_multiline_input_safe",
    "get_project_id_from_user",
    "get_shells_file",
    "get_setup_config_file",
    "get_sync_config_file",
    "handle_multiple_commands",
    "handle_shell_command",
    "is_google_drive_running",
    "is_run_environment",
    "launch_google_drive",
    "list_drive_files",
    "list_shells",
    "load_shells",
    "load_setup_config",
    "load_sync_config",
    "main",
    "open_google_drive",
    "resolve_path",
    "restart_google_drive",
    "save_shells",
    "save_setup_config",
    "save_sync_config",
    "set_global_sync_dir",
    "set_local_sync_dir",
    "setup_remote_hf_credentials",
    "shell_cd",
    "shell_ls_with_id",
    "shell_mkdir",
    "shell_pwd",
    "show_help",
    "show_setup_step_1",
    "show_setup_step_2",
    "show_setup_step_3",
    "show_setup_step_4",
    "shutdown_google_drive",
    "terminate_shell",
    "test_api_connection",
    "test_drive_folder_access",
    "test_drive_service",
    "test_remote_hf_setup",
    "test_upload_workflow",
    "upload_file_to_drive",
    "write_to_json_output",
]