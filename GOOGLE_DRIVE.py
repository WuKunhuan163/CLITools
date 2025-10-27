#!/usr/bin/env python3
"""
Google Drive主管理系统
"""

import os
import sys
import warnings
from pathlib import Path

# 抑制urllib3的SSL警告
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 设置模块搜索路径
current_dir = Path(__file__).parent
google_drive_proj_dir = current_dir / "GOOGLE_DRIVE_PROJ"
google_drive_data_dir = current_dir / "GOOGLE_DRIVE_DATA"

# 确保数据目录存在
google_drive_data_dir.mkdir(exist_ok=True)
(google_drive_data_dir / "remote_files").mkdir(exist_ok=True)

if str(google_drive_proj_dir) not in sys.path:
    sys.path.insert(0, str(google_drive_proj_dir))

# 导入重构后的管理器模块
try:
    from modules import (
        CoreUtils,
        DriveProcessManager,
        SyncConfigManager,
        SetupWizard,
        RemoteShellManager,
        DriveApiService,
        ShellCommands,
        HfCredentialsManager,
    )
except ImportError as e:
    print(f"Error: Manager module import failed: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}...")
    sys.exit(1)

class GoogleDriveMain:
    """Google Drive主管理类 (委托模式重构版本)"""
    
    def __init__(self):
        """初始化Google Drive主管理器"""
        # 从配置文件加载常量
        sys.path.insert(0, str(google_drive_proj_dir))
        from modules.config_loader import get_config
        config = get_config()
        self.HOME_URL = config.HOME_URL
        self.HOME_FOLDER_ID = config.HOME_FOLDER_ID
        self.REMOTE_ROOT_FOLDER_ID = config.REMOTE_ROOT_FOLDER_ID
        self.REMOTE_ROOT = config.REMOTE_ROOT
        
        # 初始化管理器
        self.initialize_managers()
    
    def initialize_managers(self):
        """初始化各个管理器"""
        self.core_utils = CoreUtils(None, self)
        self.drive_process_manager = DriveProcessManager(None, self)
        self.sync_config_manager = SyncConfigManager(None, self)
        self.remote_shell_manager = RemoteShellManager(None, self)
        self.drive_api_service = DriveApiService(None, self)
        self.shell_commands = ShellCommands(None, self)
        self.hf_credentials_manager = HfCredentialsManager(None, self)
    

# 创建全局实例
google_drive_main = GoogleDriveMain()

# 将所有委托方法暴露为模块级函数，保持原有API兼容性
def get_multiline_input_safe(*args, **kwargs):
    return google_drive_main.core_utils.get_multiline_input_safe(*args, **kwargs)

def is_run_environment(*args, **kwargs):
    return google_drive_main.core_utils.is_run_environment(*args, **kwargs)

def write_to_json_output(*args, **kwargs):
    return google_drive_main.core_utils.write_to_json_output(*args, **kwargs)

def copy_to_clipboard(*args, **kwargs):
    return google_drive_main.core_utils.copy_to_clipboard(*args, **kwargs)

def show_help(*args, **kwargs):
    return google_drive_main.core_utils.show_help(*args, **kwargs)

def main(*args, **kwargs):
    try:
        return google_drive_main.core_utils.main(*args, **kwargs)
    except Exception as e:
        # 在最顶层捕获所有异常并显示完整traceback
        try:
            sys.path.insert(0, str(google_drive_proj_dir))
            from modules.error_handler import capture_and_report_error
            error_info = capture_and_report_error("Top-level main execution", e)
            print(f"Top-level error: {error_info.get('exception_message', str(e))}")
            return 1
        except ImportError:
            print(f"Top-level error: {e}")
            import traceback
            traceback.print_exc()
            return 1

def is_google_drive_running(*args, **kwargs):
    return google_drive_main.drive_process_manager.is_google_drive_running(*args, **kwargs)

def get_google_drive_processes(*args, **kwargs):
    return google_drive_main.drive_process_manager.get_google_drive_processes(*args, **kwargs)

def shutdown_google_drive(*args, **kwargs):
    return google_drive_main.drive_process_manager.shutdown_google_drive(*args, **kwargs)

def launch_google_drive(*args, **kwargs):
    return google_drive_main.drive_process_manager.launch_google_drive(*args, **kwargs)

def restart_google_drive(*args, **kwargs):
    return google_drive_main.drive_process_manager.restart_google_drive(*args, **kwargs)

def get_google_drive_status(*args, **kwargs):
    return google_drive_main.sync_config_manager.get_google_drive_status(*args, **kwargs)

def open_google_drive(*args, **kwargs):
    return google_drive_main.drive_api_service.open_google_drive(*args, **kwargs)

def handle_shell_command(*args, **kwargs):
    return google_drive_main.shell_commands.handle_shell_command(*args, **kwargs)

# 保持原有的main函数调用结构
if __name__ == "__main__":
    import sys
    try:
        sys.exit(main())
    except Exception as e:
        # 使用增强的错误处理系统
        try:
            sys.path.insert(0, str(google_drive_proj_dir))
            from modules.error_handler import capture_and_report_error
            error_info = capture_and_report_error("GOOGLE_DRIVE main execution", e)
            print(f"Fatal error: {error_info.get('exception_message', str(e))}")
            sys.exit(1)
        except ImportError:
            print(f"Fatal error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1) 