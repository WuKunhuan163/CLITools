class CoreUtils:
    """核心工具管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def get_multiline_input_safe(self, *args, **kwargs):
        return get_multiline_input_safe(*args, **kwargs)
    
    def is_run_environment(self, *args, **kwargs):
        return is_run_environment(*args, **kwargs)
    
    def write_to_json_output(self, *args, **kwargs):
        return write_to_json_output(*args, **kwargs)
    
    def copy_to_clipboard(self, *args, **kwargs):
        # copy_to_clipboard现在在command_executor中
        from .command_executor import CommandExecutor
        executor_instance = CommandExecutor(None, None)
        return executor_instance.copy_to_clipboard(*args, **kwargs)
    
    def show_help(self, *args, **kwargs):
        from .help_system import show_unified_help
        return show_unified_help(*args, **kwargs)
    
    def main(self, *args, **kwargs):
        """主函数 - 直接使用GoogleDriveShell处理命令行参数"""
        try:
            # 直接使用GoogleDriveShell处理命令行参数
            import os
            import sys
            current_dir = os.path.dirname(os.path.dirname(__file__))
            sys.path.insert(0, current_dir)
            from google_drive_shell import GoogleDriveShell
            
            shell = GoogleDriveShell()
            return shell.handle_command_line_args()
        except Exception as e:
            # 如果出错，使用增强错误处理显示完整traceback
            try:
                from .error_handler import capture_and_report_error
                error_info = capture_and_report_error("CoreUtils.main GoogleDriveShell initialization", e)
                print(f"Failed to use GoogleDriveShell: {error_info.get('exception_message', str(e))}")
            except ImportError:
                print(f"Warning: Failed to use GoogleDriveShell: {e}")
                import traceback
                traceback.print_exc()
            return 1

# 独立的工具函数（从remote_commands.py迁移）
from .utils import is_run_environment, write_to_json_output
    
class DriveProcessManager:
    """驱动进程管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def is_google_drive_running(self, *args, **kwargs):
        return is_google_drive_running(*args, **kwargs)
    
    def get_google_drive_processes(self, *args, **kwargs):
        return get_google_drive_processes(*args, **kwargs)
    
    def shutdown_google_drive(self, *args, **kwargs):
        return shutdown_google_drive(*args, **kwargs)
    
    def launch_google_drive(self, *args, **kwargs):
        return launch_google_drive(*args, **kwargs)
    
    def restart_google_drive(self, *args, **kwargs):
        return restart_google_drive(*args, **kwargs)

class SyncConfigManager:
    """同步配置管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def get_sync_config_file(self, *args, **kwargs):
        return get_sync_config_file(*args, **kwargs)
    
    def load_sync_config(self, *args, **kwargs):
        return load_sync_config(*args, **kwargs)
    
    def save_sync_config(self, *args, **kwargs):
        return save_sync_config(*args, **kwargs)
    
    def set_local_sync_dir(self, *args, **kwargs):
        return set_local_sync_dir(*args, **kwargs)
    
    def set_global_sync_dir(self, *args, **kwargs):
        return set_global_sync_dir(*args, **kwargs)
    
    def get_google_drive_status(self, *args, **kwargs):
        return get_google_drive_status(*args, **kwargs)

class SetupWizard:
    """设置向导管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def show_setup_step_1(self, *args, **kwargs):
        return show_setup_step_1(*args, **kwargs)
    
    def show_setup_step_2(self, *args, **kwargs):
        return show_setup_step_2(*args, **kwargs)
    
    def show_setup_step_3(self, *args, **kwargs):
        return show_setup_step_3(*args, **kwargs)
    
    def show_setup_step_4(self, *args, **kwargs):
        return show_setup_step_4(*args, **kwargs)
        
class RemoteShellManager:
    """远程Shell管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def create_shell(self, *args, **kwargs):
        return create_shell(*args, **kwargs)
    
    def list_shells(self, *args, **kwargs):
        return list_shells(*args, **kwargs)
    
    def checkout_shell(self, *args, **kwargs):
        return checkout_shell(*args, **kwargs)
    
    def terminate_shell(self, *args, **kwargs):
        return terminate_shell(*args, **kwargs)
    
    def enter_shell_mode(self, *args, **kwargs):
        return enter_shell_mode(*args, **kwargs)

class DriveApiService:
    """Drive API服务管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def open_google_drive(self, *args, **kwargs):
        return open_google_drive(*args, **kwargs)
    
    def test_api_connection(self, *args, **kwargs):
        return test_api_connection(*args, **kwargs)
    
class ShellCommands:
    """Shell命令管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def shell_mkdir(self, *args, **kwargs):
        return shell_mkdir(*args, **kwargs)
    
    def shell_pwd(self, *args, **kwargs):
        return shell_pwd(*args, **kwargs)
    
    def handle_shell_command(self, *args, **kwargs):
        return handle_shell_command(*args, **kwargs)

class HfCredentialsManager:
    """HuggingFace凭据管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def setup_remote_hf_credentials(self, *args, **kwargs):
        return setup_remote_hf_credentials(*args, **kwargs)
    
    def test_remote_hf_setup(self, *args, **kwargs):
        return test_remote_hf_setup(*args, **kwargs)

# 将所有函数添加到当前模块的全局命名空间
import sys
current_module = sys.modules[__name__]

# 从各个子模块导入函数并添加到当前模块
from . import drive_process_manager, sync_config_manager  # core_utils已合并到remote_commands中
from . import remote_shell_manager, drive_api_service, shell_commands, hf_credentials_manager

# 收集所有子模块的函数
all_modules = [
    drive_process_manager, sync_config_manager,  # core_utils已移除
    remote_shell_manager, drive_api_service, shell_commands, hf_credentials_manager
]

# 将所有函数添加到当前模块的命名空间
for module in all_modules:
    for attr_name in dir(module):
        if not attr_name.startswith('_') and callable(getattr(module, attr_name)):
            setattr(current_module, attr_name, getattr(module, attr_name))
