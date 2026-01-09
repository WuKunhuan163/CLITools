#!/usr/bin/env python3
"""
Google Drive Modules
重构后的模块导入 - 委托模式版本
"""

# 导入所有模块的函数（保持向后兼容）
from .drive_process_manager import *
from .remote_shell_manager import *
from .drive_api_service import *
from .shell_commands import *
from .hf_credentials_manager import *
from .system_utils import is_run_environment, write_to_json_output

# 导入原有的Google Drive Shell系统类
try:
    from .cache_manager import CacheManager
    from .command_executor import CommandExecutor
    from .command_generator import CommandGenerator
    from .path_resolver import PathResolver
    from .result_processor import ResultProcessor
    from .sync_manager import SyncManager
    from .validation import Validation
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

# 简化的导出列表（只包含实际存在的类和函数）
__all__ = [
    "CacheManager",
    "CommandExecutor",
    "CommandGenerator", 
    "ResultProcessor",
    "PathResolver",
    "SyncManager",
    "Validation",
    "DriveProcessManager",
    "RemoteShellManager",
    "DriveApiService",
    "HfCredentialsManager",
    "is_run_environment",
    "write_to_json_output",
]
