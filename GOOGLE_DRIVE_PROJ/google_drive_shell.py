#!/usr/bin/env python3
"""
Google Drive Shell Management (Refactored)
Google Drive远程Shell管理系统 - 重构版本
"""

import os
import json
from pathlib import Path
from GOOGLE_DRIVE_PROJ.modules import (
    CacheManager,
    PathResolver,
    SyncManager,
    Validation
)
from GOOGLE_DRIVE_PROJ.modules.command_executor import CommandExecutor
from GOOGLE_DRIVE_PROJ.modules.command_generator import CommandGenerator
from GOOGLE_DRIVE_PROJ.modules.result_processor import ResultProcessor
from GOOGLE_DRIVE_PROJ.modules.commands import CommandRegistry
from GOOGLE_DRIVE_PROJ.modules.commands.venv_command import VenvCommand
from GOOGLE_DRIVE_PROJ.modules.commands.grep_command import GrepCommand
from GOOGLE_DRIVE_PROJ.modules.commands.python_command import PythonCommand
from GOOGLE_DRIVE_PROJ.modules.commands.ls_command import LsCommand
from GOOGLE_DRIVE_PROJ.modules.commands.mkdir_command import MkdirCommand
from GOOGLE_DRIVE_PROJ.modules.commands.edit_command import EditCommand
from GOOGLE_DRIVE_PROJ.modules.commands.navigation_command import NavigationCommand
from GOOGLE_DRIVE_PROJ.modules.commands.text_command import TextCommand
from GOOGLE_DRIVE_PROJ.modules.commands.file_command import FileCommand
from GOOGLE_DRIVE_PROJ.modules.commands.upload_command import UploadCommand
from GOOGLE_DRIVE_PROJ.modules.commands.download_command import DownloadCommand
from GOOGLE_DRIVE_PROJ.modules.commands.find_command import FindCommand
from GOOGLE_DRIVE_PROJ.modules.commands.linter_command import LinterCommand
from GOOGLE_DRIVE_PROJ.modules.commands.pip_command import PipCommand
from GOOGLE_DRIVE_PROJ.modules.commands.deps_command import DepsCommand
from GOOGLE_DRIVE_PROJ.modules.commands.pyenv_command import PyenvCommand

class GoogleDriveShell:
    """Google Drive Shell管理类 (重构版本)"""
    
    def __init__(self):
        """初始化Google Drive Shell"""
        data_dir = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA"
        self.shells_file = data_dir / "shells.json"
        self.config_file = data_dir / "cache_config.json"
        self.deletion_cache_file = data_dir / "deletion_cache.json"
        
        # 确保数据目录存在
        data_dir.mkdir(exist_ok=True)
        (data_dir / "remote_files").mkdir(exist_ok=True)
        
        # 直接初始化shell配置（不通过委托）
        self.shells_data = self.load_shells()
        
        # 直接加载缓存配置（不通过委托）
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.cache_config = json.load(f)
                    self.cache_config_loaded = True
            else:
                self.cache_config = {}
                self.cache_config_loaded = False
        except Exception as e:
            print(f"Warning: Load cache config failed: {e}")
            self.cache_config = {}
            self.cache_config_loaded = False
        
        # 初始化删除时间缓存（稍后通过cache_manager加载）
        self.deletion_cache = []
        
        # 设置常量
        self.HOME_URL = "https://drive.google.com/drive/u/0/my-drive"
        
        # 设置路径
        if self.cache_config_loaded:
            try:
                config = self.cache_config
                self.LOCAL_EQUIVALENT = config.get("local_equivalent", os.path.expanduser("~/Applications/Google Drive"))
                self.DRIVE_EQUIVALENT = config.get("drive_equivalent", "/content/drive/Othercomputers/我的 MacBook Air/Google Drive")
                self.DRIVE_EQUIVALENT_FOLDER_ID = config.get("drive_equivalent_folder_id", "1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY")
                os.makedirs(self.LOCAL_EQUIVALENT, exist_ok=True)
                pass
            except Exception:
                raise Exception("配置加载失败")
        else:
            raise Exception("配置加载失败")
        
        # 从config.json动态加载REMOTE_ROOT和REMOTE_ENV
        self.load_paths_from_config()
        
        # 动态挂载点管理：检查是否需要使用动态挂载
        self.current_mount_point = None
        self.dynamic_mode = False
        
        # 先初始化Google Drive API服务
        self.drive_service = self.load_drive_service()
        
        # 然后检查挂载点（需要drive_service进行指纹验证）
        self.check_and_setup_mount_point()

        # 初始化管理器
        self.initialize_managers()

    def load_shells(self):
        """直接加载远程shell配置（不通过委托）"""
        try:
            if self.shells_file.exists():
                with open(self.shells_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {"shells": {}, "active_shell": None}
        except Exception as e:
            print(f"Error: Failed to load shell config: {e}")
            return {"shells": {}, "active_shell": None}



    def load_drive_service(self):
        """直接加载Google Drive API服务（不通过委托）"""
        try:
            import sys
            from pathlib import Path
            api_service_path = Path(__file__).parent / "google_drive_api.py"
            if api_service_path.exists():
                sys.path.insert(0, str(api_service_path.parent))
                from google_drive_api import GoogleDriveService
                return GoogleDriveService()
            else:
                return None
        except Exception as e:
            print(f"Warning: Failed to load Google Drive API service: {e}")
            return None

    def initialize_managers(self):
        """初始化各个管理器"""
        from GOOGLE_DRIVE_PROJ.modules.remote_shell_manager import RemoteShellManager
        
        # 初始化shell管理器
        self.shell_management = RemoteShellManager(self.drive_service, self)
        
        # file_operations不再需要，所有操作通过command_registry处理
        self.file_operations = None
        
        self.cache_manager = CacheManager(self.drive_service, self)
        # 现在可以加载删除缓存了
        self.deletion_cache = self.cache_manager.load_deletion_cache()
        self.command_executor = CommandExecutor(self.drive_service, self)
        self.command_generator = CommandGenerator(self.drive_service, self)
        self.result_processor = ResultProcessor(self.drive_service, self)
        self.remote_commands = type('RemoteCommandsWrapper', (), {
            'execute_command_interface': self.command_executor.execute_command_interface,
            'execute_command': self.command_executor.execute_command,
            'generate_mv_commands': self.command_generator.generate_mv_commands,
            'generate_mkdir_commands': self.command_generator.generate_mkdir_commands,
            'generate_command_interface': self.command_generator.generate_command_interface,
            'wait_and_read_result_file': self.result_processor.wait_and_read_result_file,
        })()
        self.path_resolver = PathResolver(self.drive_service, self)
        self.sync_manager = SyncManager(self.drive_service, self)
        self.validation = Validation(self.drive_service, self)
        self.command_registry = CommandRegistry()
        self.command_registry.register(VenvCommand(self))
        self.command_registry.register(GrepCommand(self))
        self.command_registry.register(PythonCommand(self))
        self.command_registry.register(LsCommand(self))
        
        # Navigation commands (cd, pwd) - using merged NavigationCommand
        nav_cmd = NavigationCommand(self)
        self.command_registry.register_under_name(nav_cmd, "cd")
        self.command_registry.register_under_name(nav_cmd, "pwd")
        
        # Text commands (cat, read) - using merged TextCommand
        text_cmd = TextCommand(self)
        self.command_registry.register_under_name(text_cmd, "cat")
        self.command_registry.register_under_name(text_cmd, "read")
        
        # File commands (touch, rm, mv) - using merged FileCommand
        file_cmd = FileCommand(self)
        self.command_registry.register_under_name(file_cmd, "touch")
        self.command_registry.register_under_name(file_cmd, "rm")
        self.command_registry.register_under_name(file_cmd, "mv")
        
        self.command_registry.register(MkdirCommand(self))
        self.command_registry.register(EditCommand(self))
        upload_cmd = UploadCommand(self)
        self.command_registry.register(upload_cmd)
        self.command_registry.register_under_name(upload_cmd, "upload_folder")
        self.command_registry.register(DownloadCommand(self))
        self.command_registry.register(FindCommand(self))
        self.command_registry.register(LinterCommand(self))
        self.command_registry.register(PipCommand(self))
        self.command_registry.register(DepsCommand(self))
        self.command_registry.register(PyenvCommand(self))
    
    def execute_command_via_registry(self, command_name, method_name, *args, **kwargs):
        """通用的命令委托方法 - 通过command_registry执行命令"""
        command = self.command_registry.get_command(command_name)
        if command and hasattr(command, method_name):
            method = getattr(command, method_name)
            return method(*args, **kwargs)
        else:
            return {"success": False, "error": f"{command_name} command or method {method_name} not available"}
    
    
    def calculate_timeout_from_file_sizes(self, *args, **kwargs):
        """委托到sync_manager管理器"""
        return self.sync_manager.calculate_timeout_from_file_sizes(*args, **kwargs)
    
    def check_network_connection(self, *args, **kwargs):
        """委托到sync_manager管理器"""
        return self.sync_manager.check_network_connection(*args, **kwargs)
    
    def checkout_shell(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.checkout_shell(*args, **kwargs)
    
    def cmd_cat(self, *args, **kwargs):
        """委托到command_registry - CatCommand"""
        return self.execute_command_via_registry('cat', 'cmd_cat', *args, **kwargs)
    
    def cmd_cd(self, *args, **kwargs):
        """委托到command_registry - CdCommand"""
        return self.execute_command_via_registry('cd', 'cmd_cd', *args, **kwargs)
    
    def cmd_deps(self, *args, **kwargs):
        """委托到command_registry - DepsCommand"""
        return self.execute_command_via_registry('deps', 'cmd_deps', *args, **kwargs)
    
    def cmd_download(self, *args, **kwargs):
        """委托到command_registry - DownloadCommand"""
        return self.execute_command_via_registry('download', 'cmd_download', *args, **kwargs)
    
    def cmd_edit(self, *args, **kwargs):
        """委托到command_registry - EditCommand"""
        return self.execute_command_via_registry('edit', 'cmd_edit', *args, **kwargs)
    
    
    def cmd_grep(self, *args, **kwargs):
        """委托到command_registry - GrepCommand"""
        return self.execute_command_via_registry('grep', 'cmd_grep', *args, **kwargs)
    
    def cmd_ls(self, *args, **kwargs):
        """委托到command_registry - LsCommand"""
        return self.execute_command_via_registry('ls', 'cmd_ls', *args, **kwargs)

    def cmd_ls_remote(self, *args, **kwargs):
        """委托到command_registry - LsCommand"""
        return self.execute_command_via_registry('ls', 'cmd_ls_remote', *args, **kwargs)
    
    def cmd_mkdir(self, *args, **kwargs):
        """委托到command_registry - MkdirCommand"""
        return self.execute_command_via_registry('mkdir', 'cmd_mkdir', *args, **kwargs)
    
    def cmd_touch(self, *args, **kwargs):
        """委托到command_registry - TouchCommand"""
        return self.execute_command_via_registry('touch', 'cmd_touch', *args, **kwargs)
    
    def cmd_mv(self, *args, **kwargs):
        """委托到command_registry - MvCommand"""
        return self.execute_command_via_registry('mv', 'cmd_mv', *args, **kwargs)
    
    def cmd_pwd(self, *args, **kwargs):
        """委托到command_registry - PwdCommand"""
        return self.execute_command_via_registry('pwd', 'cmd_pwd', *args, **kwargs)
    
    def cmd_python(self, *args, **kwargs):
        """委托到command_registry - PythonCommand"""
        return self.execute_command_via_registry('python', 'cmd_python', *args, **kwargs)
    
    def cmd_python_code(self, code, save_output=False):
        """委托到command_registry - PythonCommand"""
        return self.execute_command_via_registry('python', 'cmd_python', code=code, save_output=save_output)
    
    def cmd_read(self, *args, **kwargs):
        """委托到command_registry - ReadCommand"""
        return self.execute_command_via_registry('read', 'cmd_read', *args, **kwargs)
    
    def cmd_rm(self, *args, **kwargs):
        """委托到command_registry - RmCommand"""
        return self.execute_command_via_registry('rm', 'cmd_rm', *args, **kwargs)
    
    def cmd_upload(self, *args, **kwargs):
        """委托到command_registry - UploadCommand"""
        return self.execute_command_via_registry('upload', 'cmd_upload', *args, **kwargs)
    
    def cmd_upload_folder(self, *args, **kwargs):
        """委托到command_registry - UploadCommand"""
        return self.execute_command_via_registry('upload', 'cmd_upload_folder', *args, **kwargs)
    
    def cmd_linter(self, *args, **kwargs):
        """委托到command_registry - LinterCommand"""
        return self.execute_command_via_registry('linter', 'cmd_linter', *args, **kwargs)
    
    def cmd_venv(self, *args, **kwargs):
        """委托到command_registry - VenvCommand"""
        return self.execute_command_via_registry('venv', 'cmd_venv', *args, **kwargs)
    
    def cmd_pyenv(self, *args, **kwargs):
        """委托到command_registry - PyenvCommand"""
        return self.execute_command_via_registry('pyenv', 'cmd_pyenv', *args, **kwargs)
    
    
    def cmd_pip(self, *args, **kwargs):
        """委托到command_registry - PipCommand"""
        return self.execute_command_via_registry('pip', 'cmd_pip', *args, **kwargs)
    
    def create_shell(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.create_shell(*args, **kwargs)
    
    def execute_command_interface(self, *args, **kwargs):
        """委托到command_executor管理器"""
        kwargs['_skip_queue_management'] = kwargs.get('_skip_queue_management', False)
        return self.command_executor.execute_command_interface(*args, **kwargs)
    
    def verify_with_ls(self, *args, **kwargs):
        """委托到validation管理器"""
        return self.validation.verify_with_ls(*args, **kwargs)
    
    def process_json(self, echo_command):
        """处理echo命令中的转义字符"""
        import re
        
        # 解析echo命令：echo "content" > filename
        patterns = [
            r'^echo\s+(?:-[ne]+\s+)?(["\'])(.*?)\1\s*>\s*(.+)$',  # 带引号格式
            r'^echo\s+(?:-[ne]+\s+)?(.*?)\s*>\s*(.+)$'  # 无引号格式
        ]
        
        for pattern in patterns:
            match = re.match(pattern, echo_command.strip(), re.DOTALL)
            if match:
                if len(match.groups()) == 3:
                    # 带引号格式
                    content = match.group(2)
                    target_file = match.group(3).strip()
                else:
                    # 无引号格式
                    content = match.group(1)
                    target_file = match.group(2).strip()
                
                # 处理转义字符（保持JSON格式的完整性）
                # 先处理双反斜杠，避免影响其他转义
                content = content.replace('\\\\', '\x00DOUBLE_BACKSLASH\x00')
                
                # 检测JSON内容：如果内容包含JSON结构，需要特殊处理引号
                is_json_like = ('{' in content and '}' in content and '\\"' in content)
                
                if is_json_like:
                    # 对于JSON内容，保持转义引号不变，稍后在重构命令时处理
                    # 不在这里转换 \"，避免双重转义
                    pass
                else:
                    # 处理转义的引号（非JSON内容）
                    content = content.replace('\\"', '"')
                    content = content.replace("\\'", "'")
                
                # 处理其他转义字符
                content = content.replace('\\n', '\n')
                content = content.replace('\\t', '\t')
                content = content.replace('\\r', '\r')
                # 恢复双反斜杠
                content = content.replace('\x00DOUBLE_BACKSLASH\x00', '\\')
                
                # 检查是否有-n选项
                has_n_option = '-n' in echo_command.split()[:3]
                
                # 重构命令时需要正确处理引号
                if is_json_like:
                    # 对于JSON内容，先将 \" 转换为实际引号，然后用单引号包围整个内容
                    # 这样可以避免bash解释内部的引号
                    json_content = content.replace('\\"', '"')
                    # 转义单引号：在bash单引号字符串中，使用'\''来表示单引号
                    json_content = json_content.replace("'", "'\\''")
                    if has_n_option:
                        return f"echo -n '{json_content}' > {target_file}"
                    else:
                        return f"echo '{json_content}' > {target_file}"
                else:
                    # 使用双引号包围内容，让bash展开变量和反引号（与本地bash行为一致）
                    # 需要转义双引号、反斜杠和美元符号以防止意外展开
                    escaped_content = content.replace('\\', '\\\\')  # 先转义反斜杠
                    escaped_content = escaped_content.replace('"', '\\"')  # 转义双引号
                    escaped_content = escaped_content.replace('$', '\\$')  # 转义美元符号（防止变量展开）
                    # 注意：不转义反引号，让它被bash执行（与本地行为一致）
                    if has_n_option:
                        return f"echo -n \"{escaped_content}\" > {target_file}"
                    else:
                        return f"echo \"{escaped_content}\" > {target_file}"
        
        # 如果解析失败，返回原命令
        return echo_command
    

    def exit_shell(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.exit_shell(*args, **kwargs)
    
    def generate_mkdir_commands(self, *args, **kwargs):
        """委托到command_generator管理器"""
        return self.command_generator.generate_mkdir_commands(*args, **kwargs)
    
    def generate_mv_commands(self, *args, **kwargs):
        """委托到command_generator管理器"""
        return self.command_generator.generate_mv_commands(*args, **kwargs)
    
    def generate_shell_id(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.generate_shell_id(*args, **kwargs)
    
    def get_current_folder_id(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.get_current_folder_id(*args, **kwargs)
    
    def get_current_shell(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.get_current_shell(*args, **kwargs)
    
    def get_remote_file_modification_time(self, *args, **kwargs):
        """委托到cache_manager管理器"""
        return self.cache_manager.get_remote_file_modification_time(*args, **kwargs)
    
    def is_cached_file_up_to_date(self, *args, **kwargs):
        """委托到cache_manager管理器"""
        return self.cache_manager.is_cached_file_up_to_date(*args, **kwargs)
    
    def is_remote_file_cached(self, *args, **kwargs):
        """委托到cache_manager管理器"""
        return self.cache_manager.is_remote_file_cached(*args, **kwargs)
    
    def list_shells(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.list_shells(*args, **kwargs)
    
    def load_cache_config(self, *args, **kwargs):
        """委托到cache_manager管理器"""
        return self.cache_manager.load_cache_config(*args, **kwargs)
    
    def move_to_local_equivalent(self, *args, **kwargs):
        """委托到sync_manager管理器"""
        return self.sync_manager.move_to_local_equivalent(*args, **kwargs)
    
    def resolve_drive_id(self, *args, **kwargs):
        """委托到path_resolver管理器"""
        return self.path_resolver.resolve_drive_id(*args, **kwargs)
    
    def resolve_remote_absolute_path(self, *args, **kwargs):
        """委托到path_resolver管理器"""
        return self.path_resolver.resolve_remote_absolute_path(*args, **kwargs)
    
    def save_deletion_cache(self, *args, **kwargs):
        """委托到cache_manager管理器"""
        return self.cache_manager.save_deletion_cache(*args, **kwargs)
    
    def save_shells(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.save_shells(*args, **kwargs)

    def terminate_shell(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.terminate_shell(*args, **kwargs)
    
    def wait_for_file_sync(self, *args, **kwargs):
        """委托到sync_manager管理器"""
        return self.sync_manager.wait_for_file_sync(*args, **kwargs)
    
    def handle_wildcard_ls(self, wildcard_path):
        """处理包含通配符的ls命令"""
        import fnmatch
        import os.path
        
        try:
            # 分离目录路径和文件名模式
            if '/' in wildcard_path:
                dir_path, pattern = wildcard_path.rsplit('/', 1)
            else:
                dir_path = "."
                pattern = wildcard_path
            
            # 解析目录路径
            current_shell = self.get_current_shell()
            if not current_shell:
                print("Error: 没有活跃的shell会话")
                return 1
            
            if dir_path == ".":
                target_folder_id = current_shell.get("current_folder_id", self.REMOTE_ROOT_FOLDER_ID)
            else:
                target_folder_id, _ = self.resolve_drive_id(dir_path, current_shell)
                if not target_folder_id:
                    print(f"Path not found: {dir_path}")
                    return 1
            
            # 直接使用Google Drive API获取目录内容，避免可能的远程命令调用
            if dir_path == ".":
                folder_id = current_shell.get("current_folder_id", self.REMOTE_ROOT_FOLDER_ID)
            else:
                folder_id, _ = self.resolve_drive_id(dir_path, current_shell)
                if not folder_id:
                    print(f"Path not found: {dir_path}")
                    return 1
            
            # 直接调用Google Drive API
            api_result = self.drive_service.list_files(folder_id=folder_id, max_results=100)
            if not api_result.get('success'):
                print(f"Error: Failed to list directory: {api_result.get('error', 'Unknown error')}")
                return 1
            
            result = {
                "success": True,
                "files": api_result.get('files', []),
                "folders": []  # list_files已经包含了所有类型的项目
            }
            
            if not result.get("success"):
                print(result.get("error", "Error: Failed to list directory"))
                return 1
            
            # 获取所有项目（files字段包含文件和文件夹）
            all_items = result.get("files", [])
            
            # 使用fnmatch进行通配符匹配
            matched_items = []
            for item in all_items:
                item_name = item.get('name', '')
                if fnmatch.fnmatch(item_name, pattern):
                    matched_items.append(item)
            
            # 显示匹配的项目
            if matched_items: 
                folders = [item for item in matched_items if item.get('mimeType') == 'application/vnd.google-apps.folder']
                files = [item for item in matched_items if item.get('mimeType') != 'application/vnd.google-apps.folder']
                
                sorted_folders = sorted(folders, key=lambda x: x.get('name', '').lower())
                sorted_files = sorted(files, key=lambda x: x.get('name', '').lower())
                
                all_sorted_items = sorted_folders + sorted_files
                
                for item in all_sorted_items:
                    name = item.get('name', 'Unknown')
                    if item.get('mimeType') == 'application/vnd.google-apps.folder':
                        print(f"{name}/")
                    else:
                        print(name)
            
            return 0
            
        except Exception as e:
            print(f"Error: Wildcard matching failed: {e}")
            return 1

    def sync_venv_state_to_local_shell(self, venv_args):
        """同步虚拟环境状态到本地shell配置"""
        try:
            import time
            
            # 检查是否是会改变venv状态的命令
            if not venv_args or venv_args[0] not in ['--activate', '--deactivate']:
                return
            
            # 获取当前shell
            current_shell = self.get_current_shell()
            if not current_shell:
                return
            
            # 使用统一的venv --current接口获取最新状态
            current_result = self.cmd_venv("--current")
            
            if current_result.get("success"):
                # 解析当前激活的环境 - 适配实际的返回格式
                current_env = current_result.get("current")
                # 如果current字段为空或"None"，设置为None
                if current_env == "None" or not current_env:
                    current_env = None
                
                # 更新本地shell状态
                shells_data = self.load_shells()
                shell_id = current_shell['id']
                
                if shell_id in shells_data["shells"]:
                    # 确保venv_state字段存在
                    if "venv_state" not in shells_data["shells"][shell_id]:
                        shells_data["shells"][shell_id]["venv_state"] = {}
                    
                    # 更新虚拟环境状态
                    shells_data["shells"][shell_id]["venv_state"]["active_env"] = current_env
                    shells_data["shells"][shell_id]["last_accessed"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 保存到本地
                    self.save_shells(shells_data)
                    
        except Exception as e:
            # 如果同步失败，不影响venv命令的正常执行
            pass
    
    def execute_background_command(self, shell_cmd, command_identifier=None):
        """执行background命令 - 使用echo命令构建，完全避免f-string嵌套引号"""
        import time
        import random
        import base64
        from datetime import datetime
        from modules.config_loader import get_bg_status_file, get_bg_script_file, get_bg_log_file, get_bg_result_file
        
        try:
            # 获取当前shell
            current_shell = self.get_current_shell()
            if not current_shell:
                print(f"Error: 没有活跃的shell会话")
                return 1
            
            # 改进的语法检查 - 正确处理复杂引号
            try:
                import subprocess
                import tempfile
                import os
                
                # 准备要检查的命令内容
                # 如果shell_cmd被引号包围，需要去除外层引号
                cmd_to_check = shell_cmd.strip()
                if ((cmd_to_check.startswith('"') and cmd_to_check.endswith('"')) or
                    (cmd_to_check.startswith("'") and cmd_to_check.endswith("'"))):
                    cmd_to_check = cmd_to_check[1:-1]
                
                # 创建临时脚本文件进行语法检查
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_file:
                    # 写入shebang
                    temp_file.write("#!/bin/bash\n")
                    
                    # 写入去除外层引号的命令
                    temp_file.write(cmd_to_check)
                    temp_file.write("\n")  # 确保命令以换行结尾
                    
                    temp_file_path = temp_file.name
                
                # 执行语法检查
                result = subprocess.run(['bash', '-n', temp_file_path], capture_output=True, text=True, timeout=5)
                os.unlink(temp_file_path)
                
                if result.returncode != 0:
                    print(f"Error: Bash syntax error in command: {shell_cmd}")
                    print(f"Error: {result.stderr.strip()}")
                    return 1
                    
            except Exception as e:
                print(f"Warning: Could not check syntax: {e}")
            
            # 生成background PID
            bg_pid = f"{int(time.time())}_{random.randint(1000, 9999)}"
            start_time = datetime.now().isoformat()
            
            # 获取路径信息
            tmp_path = f"{self.REMOTE_ROOT}/tmp"
            
            # 使用常量构建文件名
            status_file = get_bg_status_file(bg_pid)
            script_file = get_bg_script_file(bg_pid)
            log_file = get_bg_log_file(bg_pid)
            result_file = get_bg_result_file(bg_pid)
            
            # 使用base64编码来安全传递命令，避免引号问题
            cmd_b64 = base64.b64encode(shell_cmd.encode('utf-8')).decode('ascii')
            
            # 构建命令使用简单字符串拼接 - 完全避免f-string嵌套引号
            cmd_parts = []
            
            # Part 1: Setup
            cmd_parts.append("# Final solution - NO quote escaping issues")
            cmd_parts.append(f"mkdir -p {tmp_path}")
            cmd_parts.append("")
            
            # Part 2: Create status helper script using simple echo commands
            cmd_parts.append("# Create status helper script using echo (no heredoc)")
            cmd_parts.append(f"echo 'import json, base64, sys' > {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'cmd = base64.b64decode(sys.argv[1]).decode(\"utf-8\")' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'pid = sys.argv[2]' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'status_type = sys.argv[3]' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'start_time = sys.argv[4]' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'status_file = sys.argv[5]' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'if status_type == \"starting\":' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    data = {{\"pid\": pid, \"command\": cmd, \"status\": \"starting\", \"start_time\": start_time, \"result_file\": None}}' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'elif status_type == \"running\":' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    real_pid = int(sys.argv[6])' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    result_file = sys.argv[7]' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    data = {{\"pid\": pid, \"real_pid\": real_pid, \"command\": cmd, \"status\": \"running\", \"start_time\": start_time, \"result_file\": result_file}}' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'elif status_type == \"completed\":' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    end_time = sys.argv[6]' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    exit_code = int(sys.argv[7])' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    result_file = sys.argv[8]' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    data = {{\"pid\": pid, \"command\": cmd, \"status\": \"completed\", \"start_time\": start_time, \"end_time\": end_time, \"exit_code\": exit_code, \"result_file\": result_file}}' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'with open(status_file, \"w\") as f:' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    json.dump(data, f, ensure_ascii=False)' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append("")
            
            # Part 3: Create initial status
            cmd_parts.append("# Create initial status")
            cmd_parts.append(f"python3 {tmp_path}/status_helper_{bg_pid}.py {cmd_b64} {bg_pid} starting {start_time} {tmp_path}/{status_file}")
            cmd_parts.append("")
            
            # Part 4: Create execution script using echo commands
            cmd_parts.append("# Create execution script using echo (no heredoc)")
            cmd_parts.append(f"echo '#!/bin/bash' > {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'set -e' >> {tmp_path}/{script_file}")
            # Immediately create log file to ensure it exists when task starts
            cmd_parts.append(f"echo 'touch {tmp_path}/{log_file}' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'echo {cmd_b64} | base64 -d > /tmp/bg_cmd_result_{bg_pid}.sh' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'chmod +x /tmp/bg_cmd_result_{bg_pid}.sh' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'bash /tmp/bg_cmd_result_{bg_pid}.sh > /tmp/bg_stdout_{bg_pid} 2> /tmp/bg_stderr_{bg_pid}' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'EXIT_CODE=$?' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'rm -f /tmp/bg_cmd_result_{bg_pid}.sh' >> {tmp_path}/{script_file}")
            
            # Add result generation using a separate Python script to avoid quote escaping
            cmd_parts.append(f"echo 'cat > {tmp_path}/create_result_{bg_pid}.py << \"RESULT_PYTHON_EOF\"' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'import json, os, sys' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'from datetime import datetime' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'exit_code = int(sys.argv[1])' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'stdout_file = \"/tmp/bg_stdout_{bg_pid}\"' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'stderr_file = \"/tmp/bg_stderr_{bg_pid}\"' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'stdout_content = \"\"' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'stderr_content = \"\"' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'if os.path.exists(stdout_file):' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '    with open(stdout_file, \"r\") as f:' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '        stdout_content = f.read()' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'if os.path.exists(stderr_file):' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '    with open(stderr_file, \"r\") as f:' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '        stderr_content = f.read()' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'result = {{' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '    \"success\": exit_code == 0,' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '    \"data\": {{' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '        \"exit_code\": exit_code,' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '        \"stdout\": stdout_content,' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '        \"stderr\": stderr_content,' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '        \"working_dir\": os.getcwd(),' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '        \"timestamp\": datetime.now().isoformat()' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '    }}' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '}}' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'with open(\"{tmp_path}/{result_file}\", \"w\") as f:' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '    json.dump(result, f, indent=2, ensure_ascii=False)' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'RESULT_PYTHON_EOF' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'python3 {tmp_path}/create_result_{bg_pid}.py $EXIT_CODE' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'rm -f {tmp_path}/create_result_{bg_pid}.py' >> {tmp_path}/{script_file}")
            
            # Clean up and update status
            cmd_parts.append(f"echo 'rm -f /tmp/bg_stdout_{bg_pid} /tmp/bg_stderr_{bg_pid}' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'python3 {tmp_path}/status_helper_{bg_pid}.py {cmd_b64} {bg_pid} completed {start_time} {tmp_path}/{status_file} \"$(date -Iseconds 2>/dev/null || date)\" $EXIT_CODE {result_file}' >> {tmp_path}/{script_file}")
            cmd_parts.append("")
            
            # Part 5: Execute
            cmd_parts.append("# Execute background task")
            cmd_parts.append(f"chmod +x {tmp_path}/{script_file}")
            cmd_parts.append(f"({tmp_path}/{script_file} > {tmp_path}/{log_file} 2>&1) &")
            cmd_parts.append("REAL_PID=$!")
            cmd_parts.append("")
            
            # Part 6: Update status with real PID
            cmd_parts.append("# Update status with real PID")
            cmd_parts.append(f"python3 {tmp_path}/status_helper_{bg_pid}.py {cmd_b64} {bg_pid} running {start_time} {tmp_path}/{status_file} $REAL_PID {result_file}")
            cmd_parts.append("")
            
            # Part 7: Clean up
            cmd_parts.append("# Clean up helper script")
            cmd_parts.append(f"rm -f {tmp_path}/status_helper_{bg_pid}.py")
            
            bg_create_cmd = '\n'.join(cmd_parts)
            
            # 显示生成的命令
            
            # 设置后台模式标志
            current_shell_copy = current_shell.copy()
            current_shell_copy["_background_mode"] = True
            current_shell_copy["_background_pid"] = bg_pid
            current_shell_copy["_background_original_cmd"] = shell_cmd
            
            # 生成远程命令
            remote_command, result_filename, cmd_hash = self.command_generator.generate_command(
                bg_create_cmd, None, current_shell_copy
            )
            
            # 执行远程命令
            result = self.command_executor.execute_command(
                remote_command=remote_command,
                result_filename=result_filename,
                cmd_hash=cmd_hash,
                raw_command=bg_create_cmd
            )
            
            # 显示执行结果
            
            # 处理统一接口的结果
            if result.get("success", False):
                data = result.get("data", {})
                stdout = data.get("stdout", "").strip()
                stderr = data.get("stderr", "").strip()
                
                if stdout:
                    print(stdout)
                if stderr:
                    import sys
                    print(stderr, file=sys.stderr)
                
                # 显示后台任务信息
                print(f"Background task started with ID: {bg_pid}")
                print(f"Command: {shell_cmd}")
                print("")
                print("Run the following commands to track the background task status:")
                print(f"  GDS --bg --status {bg_pid}    # Check task status")
                print(f"  GDS --bg --result {bg_pid}    # View task result")
                print(f"  GDS --bg --log {bg_pid}       # View task log")
                print(f"  GDS --bg --cleanup {bg_pid}   # Clean up task files")
                
                return 0
            else:
                # 添加详细的错误信息和traceback
                import traceback
                
                error_msg = result.get("error", "Background task creation failed")
                print(f"Failed to create background task: {error_msg}")
                
                # 显示详细错误信息（如果有的话）
                if 'debug_info' in result:
                    print("Detailed error information available in result debug_info")
                else:
                    print("Check the error details above for more information.")
                
                print("\nCall stack (most recent call last):")
                stack_lines = traceback.format_stack()[-10:]
                for i, line in enumerate(stack_lines, 1):
                    # 清理和格式化每一行
                    clean_line = line.strip().replace('\n', ' ')
                    print(f"{i:2d}. {clean_line}")
                    if i < len(stack_lines):  # 不是最后一行时添加空行
                        print()
                
                return 1
                
        except Exception as e:
            print(f"Error executing background command: {e}")
            return 1

    def execute_shell_command(self, shell_cmd, command_identifier=None):
        """执行shell命令 - 使用WindowManager的新架构入口点"""
        
        # 保存原始用户命令，用于后续的文件验证分析
        self._original_user_command = shell_cmd.strip()
        try:
            is_quoted_command = shell_cmd.startswith("__QUOTED_COMMAND__")
            if is_quoted_command:
                shell_cmd = shell_cmd[len("__QUOTED_COMMAND__"):]
            
            # 首先检测引号包围的完整命令（在命令解析之前）
            shell_cmd_clean = shell_cmd.strip()
            
            if ((shell_cmd_clean.startswith("'") and shell_cmd_clean.endswith("'")) or 
                (shell_cmd_clean.startswith('"') and shell_cmd_clean.endswith('"'))):
                shell_cmd_clean = shell_cmd_clean[1:-1]
                shell_cmd = shell_cmd_clean
                is_quoted_command = True
            
            # 预处理命令：检测并翻译heredoc语法
            from modules.heredoc_translator import preprocess_command
            processed_commands, needs_sequential = preprocess_command(shell_cmd_clean)
            
            # 如果检测到heredoc（无论是否多命令）
            if needs_sequential:
                if len(processed_commands) > 1:
                    # print(f"Heredoc detected, translating to {len(processed_commands)} commands:")
                    # for i, cmd in enumerate(processed_commands, 1):
                    #     print(f"  {i}. {cmd}")
                    
                    last_result = 0
                    for cmd in processed_commands:
                        # 递归调用，但使用翻译后的单个命令
                        result = self.execute_shell_command(cmd, command_identifier)
                        if isinstance(result, int):
                            last_result = result
                            if result != 0:
                                return result  # 如果任何命令失败，立即返回
                        else:
                            last_result = 0
                    return last_result
                else:
                    # 单个命令的heredoc翻译
                    print(f"Heredoc detected, translating to: {processed_commands[0]}")
                    # 继续使用翻译后的命令
            
            # 如果是翻译后的命令，使用翻译结果
            if needs_sequential:
                shell_cmd_clean = processed_commands[0]
                shell_cmd = shell_cmd_clean

            # 首先检查特殊命令（不需要远程执行）
            if shell_cmd_clean in ['--help', '-h', 'help']:
                from modules.help_system import show_unified_help
                return show_unified_help(context="shell", command_identifier=command_identifier)
            
            # 检查background选项
            background_options = ['--background', '--bg', '--async']
            for bg_option in background_options:
                if shell_cmd_clean.startswith(bg_option + ' ') or shell_cmd_clean == bg_option:
                    remaining_cmd = shell_cmd_clean[len(bg_option):].strip()
                    if remaining_cmd.startswith('--status'):
                        # GDS --bg --status [task_id]
                        status_args = remaining_cmd[8:].strip()  # 移除--status
                        if status_args:
                            return self.show_background_status(status_args, command_identifier)
                        else:
                            return self.show_all_background_status(command_identifier)
                    elif remaining_cmd.startswith('--log '):
                        # GDS --bg --log <task_id>
                        task_id = remaining_cmd[6:].strip()  # 移除--log 
                        return self._show_background_log(task_id, command_identifier)
                    elif remaining_cmd.startswith('--result '):
                        # GDS --bg --result <task_id>
                        task_id = remaining_cmd[9:].strip()  # 移除--result 
                        return self._show_background_result(task_id, command_identifier)
                    elif remaining_cmd.startswith('--cleanup'):
                        # GDS --bg --cleanup [task_id]
                        cleanup_args = remaining_cmd[9:].strip()  # 移除--cleanup
                        if cleanup_args:
                            return self._cleanup_background_task(cleanup_args, command_identifier)
                        else:
                            return self._cleanup_background_tasks(command_identifier)
                    elif remaining_cmd.startswith('--wait '):
                        # GDS --bg --wait <task_id>
                        task_id = remaining_cmd[7:].strip()  # 移除--wait 
                        return self.wait_background_task(task_id, command_identifier)
                    elif remaining_cmd == '':
                        # 只有--bg，显示帮助
                        print("GDS Background Commands:")
                        print("  --bg <command>           # Run command in background")
                        print("  --bg --status [task_id]  # Show task status")
                        print("  --bg --log <task_id>     # Show task log")
                        print("  --bg --result <task_id>  # Show task result")
                        print("  --bg --wait <task_id>    # Wait for task")
                        print("  --bg --cleanup [task_id] # Clean up tasks")
                        print("")
                        print("Alternative short forms:")
                        print("  --status [task_id]       # Show task status")
                        print("  --log <task_id>          # Show task log")
                        print("  --result <task_id>       # Show task result")
                        print("  --wait <task_id>         # Wait for task")
                        print("  --cleanup [task_id]      # Clean up tasks")
                        return 0
                    else:
                        # 执行background命令
                        return self.execute_background_command(remaining_cmd, command_identifier)
                    break
            
            # 解析命令
            has_multiple_ops = False
            for op in [' && ', ' || ', ' | ', '&&', '||', '|']:
                if op in shell_cmd_clean: 
                    if self.is_operator_outside_quotes(shell_cmd_clean, op):
                        has_multiple_ops = True
                        break
            
            # 单独检查重定向符号，因为它们需要特殊处理
            has_redirection = False
            if not has_multiple_ops:  # 只有在没有多操作符时才检查重定向
                for redir_op in [' > ', ' >> ', '>', '>>']:
                    if redir_op in shell_cmd_clean:
                        if self.is_operator_outside_quotes(shell_cmd_clean, redir_op):
                            has_redirection = True
                            break
            
            if has_multiple_ops:
                import os
                import sys
                current_dir = os.path.dirname(__file__)
                modules_dir = os.path.join(current_dir, 'modules')
                if modules_dir not in sys.path:
                    sys.path.append(modules_dir)
                
                from modules.shell_commands import handle_multiple_commands
                return handle_multiple_commands(shell_cmd_clean, command_identifier, shell_instance=self)
            
            # 然后检查是否为特殊命令（导航命令等）
            first_word = shell_cmd_clean.split()[0] if shell_cmd_clean.split() else ""

            # 如果命令包含重定向，跳过特殊命令处理，直接执行bash命令
            if has_redirection:
                # 检查是否包含特殊命令，如果是则给出警告
                special_commands_list = ['pwd', 'ls', 'cd', 'cat', 'mkdir', 'touch', 'pyenv', 
                                        'linter', 'pip', 'deps', 'edit', 'read', 
                                        'upload', 'upload-folder', 'download', 'mv', 'find', 'rm', 
                                        'grep', 'python', 'venv']
                first_word_for_check = shell_cmd_clean.split()[0] if shell_cmd_clean.split() else ""
                if first_word_for_check in special_commands_list or self.command_registry.is_special_command(first_word_for_check):
                    print(f"⚠️  Warning: Special command '{first_word_for_check}' detected with redirection. GDS special commands will be executed as standard remote bash commands. ")
                
                current_shell = self.get_current_shell()
                if current_shell:
                    result = self.execute_command_interface("bash", ["-c", shell_cmd_clean])
                    if result.get("success"):
                        return 0
                    else:
                        error_msg = result.get("error", "Command execution failed")
                        print(error_msg)
                        return 1
                else:
                    print("Error: No active remote shell")
                    return 1

            # 首先检查新的命令注册系统
            if self.command_registry.is_special_command(first_word):
                import shlex
                try:
                    cmd_parts = shlex.split(shell_cmd_clean)
                    if cmd_parts:
                        cmd = cmd_parts[0]
                        args = cmd_parts[1:]
                        
                        # 统一处理所有参数的路径扩展
                        processed_args = []
                        for arg in args:
                            if arg.startswith('/') and not arg.startswith('/content/'):
                                # 这可能是被bash扩展的本地路径，需要转换
                                converted_arg = self.path_resolver.undo_local_path_user_expansion(arg)
                                processed_args.append(converted_arg)
                            else:
                                processed_args.append(arg)
                        args = processed_args
                    else:
                        raise Exception("Empty command after parsing")
                except Exception as e:
                    raise Exception(f"Command parsing failed: {e}")
                
                # 使用命令注册系统执行命令
                return self.command_executor.execute_special_command(cmd, args)
            
            # 回退到旧的特殊命令处理系统
            special_commands = ['pwd', 'ls', 'cd', 'cat', 'mkdir', 'touch', 'help', 'pyenv', 
                              'cleanup-windows', 'linter', 'pip', 'deps', 'edit', 'read', 
                              'upload', 'upload-folder', 'download', 'mv', 'find', 'rm']
            if first_word in special_commands:
                import shlex
                try:
                    cmd_parts = shlex.split(shell_cmd_clean)
                    if cmd_parts:
                        cmd = cmd_parts[0]
                        args = cmd_parts[1:]
                        
                        # 统一处理所有参数的路径扩展
                        processed_args = []
                        for arg in args:
                            if arg.startswith('/') and not arg.startswith('/content/'):
                                # 这可能是被bash扩展的本地路径，需要转换
                                converted_arg = self.path_resolver.undo_local_path_user_expansion(arg)
                                processed_args.append(converted_arg)
                            else:
                                processed_args.append(arg)
                        args = processed_args
                    else:
                        raise Exception("Empty command after parsing")
                except Exception as e:
                    raise Exception(f"Command parsing failed: {e}")
                
                # 所有特殊命令统一使用命令执行系统
                return self.command_executor.execute_special_command(cmd, args)
             
            # 如果不是特殊命令，使用统一的命令解析和转译接口
            if is_quoted_command:
                translated_cmd = shell_cmd_clean
            else:
                translation_result = self.execute_generic_command(shell_cmd_clean)
                if not translation_result["success"]:
                    raise Exception(f"Error: {translation_result['error']}")
                translated_cmd = translation_result["translated_command"]
            
            # 使用execute_command_interface统一接口
            result = self.execute_command_interface("bash", ["-c", translated_cmd], _original_user_command=translated_cmd)
            
            # 处理结果
            if not result.get("success"): 
                raise Exception(f"Command execution returned failure: {result.get('error', 'Unknown error')}")
            
            data = result.get("data", {})
            stdout = data.get("stdout", "").strip()
            stderr = data.get("stderr", "").strip()
            if stdout:
                print(stdout)
            if stderr:
                import sys
                print(stderr, file=sys.stderr)
            return 0
                
        except Exception as e:
            # 使用增强的错误处理系统显示完整traceback
            try:
                from GOOGLE_DRIVE_PROJ.modules.error_handler import capture_and_report_error
                capture_and_report_error("Shell command execution", e, {
                    "command": shell_cmd,
                    "command_identifier": command_identifier
                })
                print(f"Google Drive Shell command execution failed with detailed traceback above. ")
                return 1
            except ImportError:
                error_msg = f"Error: Error executing shell command: {e}"
                print(error_msg)
                import traceback
                traceback.print_exc()
                return 1
        finally: 
            pass

    def show_background_status(self, bg_pid, command_identifier=None):
        """显示background任务状态 - 优先从status文件读取，如果不存在则从result文件读取"""
        try:
            import json
            
            # 首先尝试读取status文件
            status_data = self._read_background_file(bg_pid, 'status', command_identifier)
            
            if status_data.get("success", False):
                # status文件存在，说明任务正在运行或刚启动
                data = status_data.get("data", {})
                status_content = data.get("stdout", "").strip()
                
                if status_content:
                    try:
                        status_json = json.loads(status_content)
                        
                        # 提取状态信息
                        status = status_json.get("status", "unknown")
                        command = status_json.get("command", "N/A")
                        start_time = status_json.get("start_time", "N/A")
                        end_time = status_json.get("end_time", "")
                        pid = status_json.get("pid", bg_pid)
                        real_pid = status_json.get("real_pid", None)
                        
                        # 获取日志大小
                        log_result = self._read_background_file(bg_pid, 'log', command_identifier)
                        log_size = 0
                        if log_result.get("success", False):
                            log_data = log_result.get("data", {})
                            log_content = log_data.get("stdout", "")
                            log_size = len(log_content.encode('utf-8'))
                        
                        # 显示状态信息
                        print(f"Status: {status}")
                        if status == "running":
                            if real_pid:
                                print(f"PID: {pid} (Real PID: {real_pid})")
                            else:
                                print(f"PID: {pid}")
                        else:
                            print(f"PID: {pid}")
                        
                        print(f"Command: {command}")
                        print(f"Start time: {start_time}")
                        
                        if end_time:
                            print(f"End time: {end_time}")
                        
                        print(f"Log size: {log_size} bytes")
                        
                        return 0
                        
                    except json.JSONDecodeError as e:
                        print(f"Error: Invalid JSON in status file: {e}")
                        return 1
            
            # status文件不存在，尝试读取result文件（任务已完成）
            result_data = self._read_background_file(bg_pid, 'result', command_identifier)
            if not result_data.get("success", False):
                print(f"Error: Background task {bg_pid} not found")
                return 1
            
            data = result_data.get("data", {})
            result_content = data.get("stdout", "").strip()
            if not result_content:
                print(f"Error: Background task {bg_pid} result file is empty")
                return 1
            
            try:
                result_json = json.loads(result_content)
                
                # 从result文件中提取status（如果有）
                # result文件可能包含嵌套的data结构
                if "data" in result_json:
                    # 新格式：有嵌套data
                    inner_data = result_json["data"]
                    exit_code = inner_data.get("exit_code", None)
                    status = result_json.get("status", "unknown")
                else:
                    # 旧格式：平坦结构
                    exit_code = result_json.get("exit_code", None)
                    status = result_json.get("status", "unknown")
                
                command = result_json.get("command", "N/A")
                start_time = result_json.get("start_time", "N/A")
                end_time = result_json.get("end_time", "N/A")
                pid = result_json.get("pid", bg_pid)
                
                # 获取日志大小
                log_result = self._read_background_file(bg_pid, 'log', command_identifier)
                log_size = 0
                if log_result.get("success", False):
                    log_data = log_result.get("data", {})
                    log_content = log_data.get("stdout", "")
                    log_size = len(log_content.encode('utf-8'))
                
                # 显示状态信息
                print(f"Status: {status}")
                if status == "running":
                    print(f"PID: {pid}")
                else:
                    print(f"PID: {pid} (finished)")
                
                print(f"Command: {command}")
                print(f"Start time: {start_time}")
                
                if status == "completed" and end_time and end_time != "N/A":
                    print(f"End time: {end_time}")
                
                if exit_code is not None:
                    print(f"Exit code: {exit_code}")
                
                print(f"Log size: {log_size} bytes")
                
                return 0
                
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in result file: {e}")
                return 1
                
        except Exception as e:
            print(f"Error: Failed to check status: {e}")
            return 1

    def show_all_background_status(self, command_identifier=None):
        """显示所有background任务状态"""
        try:
            current_shell = self.get_current_shell()
            if not current_shell:
                print(f"Error: 没有活跃的shell会话")
                return 1
            
            # 构建查询所有状态的远程命令
            status_cmd = f'''
REMOTE_ROOT="{self.REMOTE_ROOT}"
TMP_DIR="$REMOTE_ROOT/tmp"

if [ ! -d "$TMP_DIR" ]; then
    echo "No background tasks found"
    exit 0
fi

# 创建临时文件存储任务信息
TEMP_FILE="/tmp/gds_tasks_$$.txt"

FOUND_TASKS=0
for result_file in "$TMP_DIR"/cmd_bg_*.result.json; do
    if [ -f "$result_file" ]; then
        FOUND_TASKS=1
        BG_PID=$(basename "$result_file" .result.json | sed 's/cmd_bg_//')
        
        # 读取result文件并解析状态信息
        RESULT_DATA=$(cat "$result_file")
        
        # 从result文件中提取命令和时间信息
        COMMAND=$(echo "$RESULT_DATA" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('command', 'Unknown'))" 2>/dev/null || echo "Unknown")
        END_TIME=$(echo "$RESULT_DATA" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('end_time', 'Unknown'))" 2>/dev/null || echo "Unknown")
        
        # 检查任务是否还在运行（通过检查end_time）
        if [ "$END_TIME" = "Unknown" ] || [ "$END_TIME" = "null" ] || [ -z "$END_TIME" ]; then
            STATUS="running"
        else
            STATUS="completed"
        fi
        
        # 截断命令到前20个字符
        COMMAND_SHORT=$(echo "$COMMAND" | cut -c1-20)
        if [ ${{#COMMAND}} -gt 20 ]; then
            COMMAND_SHORT="$COMMAND_SHORT..."
        fi
        
        # 将任务信息写入临时文件，用于排序
        echo "$BG_PID|$STATUS|$COMMAND_SHORT" >> "$TEMP_FILE"
    fi
done

if [ $FOUND_TASKS -eq 0 ]; then
    echo "No background tasks found"
else
    # 显示表格头部
    echo "Background Tasks:"
    printf "%-18s | %-9s | %s\\n" "Task ID" "Status" "Command (first 20 chars)"
    printf "%-18s-+-%-9s-+-%s\\n" "------------------" "---------" "--------------------"
    
    # 按PID排序并显示
    sort -t'|' -k1,1n "$TEMP_FILE" | while IFS='|' read -r pid status command; do
        printf "%-18s | %-9s | %s\\n" "$pid" "$status" "$command"
    done
    
    # 清理临时文件
    rm -f "$TEMP_FILE"
fi
'''
            
            # 执行状态查询 - 使用与单个任务状态查询相同的方法
            result = self.execute_command_interface("bash", ["-c", status_cmd])
            
            # 处理结果 - 使用与单个任务状态查询相同的格式
            if result.get("success", False):
                data = result.get("data", {})
                stdout = data.get("stdout") if "stdout" in data else result.get("stdout", "")
                stderr = data.get("stderr") if "stderr" in data else result.get("stderr", "")
                stdout = (stdout or "").strip()
                stderr = (stderr or "").strip()
                
                # 统一在命令处理结束后打印输出
                if stdout:
                    print(stdout)
                if stderr:
                    import sys
                    print(stderr, file=sys.stderr)
                return 0
            else:
                error_msg = result.get("error", "Failed to check status")
                print(f"Error: {error_msg}")
                return 1
                
        except Exception as e:
            print(f"Error: Status check failed: {e}")
            return 1

    def _show_background_log(self, bg_pid, command_identifier=None):
        """显示background任务日志 - 直接读取.log文件"""
        try:
            # 直接读取.log文件，包含所有输出信息
            result = self._read_background_file(bg_pid, 'log', command_identifier)
            
            if result.get("success", False):
                data = result.get("data", {})
                stdout = data.get("stdout", "").strip()
                stderr = data.get("stderr", "").strip()
                
                if stdout:
                    print(stdout)
                elif stderr:
                    import sys
                    print(stderr, file=sys.stderr)
                else:
                    print(f"Log file for task {bg_pid} is empty or task hasn't started producing output yet.")
                
                return 0
            else:
                error_msg = result.get("error", "Log view failed")
                if "does not exist" in error_msg.lower():
                    print(f"Log file for task {bg_pid} not found. Task may not have started producing output yet.")
                    print(f"Use 'GDS --bg --status {bg_pid}' to check if the task is running.")
                else:
                    print(f"Error: {error_msg}")
                return 1
                
        except Exception as e:
            print(f"Error: Log view failed: {e}")
            return 1

    def wait_background_task(self, bg_pid, command_identifier=None):
        """等待background任务完成"""
        try:
            current_shell = self.get_current_shell()
            if not current_shell:
                print(f"Error: 没有活跃的shell会话")
                return 1
            
            # 构建等待任务的远程命令
            wait_cmd = f'''
if [ ! -f ~/tmp/cmd_bg_{bg_pid}.status ]; then
    echo "Error: Background task {bg_pid} not found"
    exit 1
fi

echo "Waiting for task {bg_pid} to complete..."

while true; do
    STATUS_DATA=$(cat ~/tmp/cmd_bg_{bg_pid}.status)
    REAL_PID=$(echo "$STATUS_DATA" | grep -o '"real_pid":[0-9]*' | cut -d':' -f2)
    
    if [ -n "$REAL_PID" ] && ps -p $REAL_PID > /dev/null 2>&1; then
        echo "Task still running (PID: $REAL_PID)..."
        sleep 5
    else
        echo "Task {bg_pid} completed!"
        
        # 显示最后的日志
        if [ -f ~/tmp/cmd_bg_{bg_pid}.log ]; then
            echo ""
            echo "=== Final Output ==="
            tail -20 ~/tmp/cmd_bg_{bg_pid}.log
        fi
        break
    fi
done
'''
            
            # 执行等待
            remote_command_info = self.command_generator.generate_command_interface("bash", ["-c", wait_cmd], current_shell)
            remote_command, result_filename = remote_command_info
            
            result = self.command_executor.show_remote_command_window(
                title=f"GDS Wait Task: {bg_pid}",
                cmd=remote_command,
                timeout_seconds=3600  # 1小时超时
            )
            
            if result["action"] == "success":
                result_data = self.result_processor.wait_and_read_result_file(result_filename)
                if result_data.get("success"):
                    stdout_content = result_data.get("data", {}).get("stdout", "")
                    if stdout_content:
                        print(stdout_content)
                    return 0
                else:
                    print(f"Error: {result_data.get('error', 'Wait failed')}")
                    return 1
            else:
                print(f"Error: Failed to wait for task: {result.get('error', 'Unknown error')}")
                return 1
                
        except Exception as e:
            print(f"Error: Wait failed: {e}")
            return 1

    def is_operator_outside_quotes(self, shell_cmd, operator):
        """
        检查操作符是否在引号外（改进版，正确处理转义字符）
        
        Args:
            shell_cmd (str): shell命令
            operator (str): 要检查的操作符
            
        Returns:
            bool: True如果操作符在引号外
        """
        in_single_quote = False
        in_double_quote = False
        i = 0
        op_len = len(operator)
        
        while i < len(shell_cmd):
            char = shell_cmd[i]
            
            # 处理转义字符（但只在双引号内或引号外有效，单引号内反斜杠无效）
            if char == '\\' and not in_single_quote and i + 1 < len(shell_cmd):
                # 跳过下一个字符
                i += 2
                continue
            
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif not in_single_quote and not in_double_quote:
                # 检查是否匹配操作符
                if i + op_len <= len(shell_cmd) and shell_cmd[i:i+op_len] == operator:
                    return True
            
            i += 1
        
        return False

    def detect_redirection(self, command_str):
        """
        智能检测命令中是否包含重定向操作符（忽略引号内的操作符）
        
        Args:
            command_str: 命令字符串
            
        Returns:
            bool: 如果包含有效的重定向操作符返回True，否则False
        """
        # 重定向操作符列表（按长度降序排列，优先匹配长的）
        redirect_operators = ['>>>', '>>', '>&', '&>', '2>', '1>', '<&', '<<', '>', '<', '|']
        
        i = 0
        in_single_quote = False
        in_double_quote = False
        
        while i < len(command_str):
            char = command_str[i]
            
            # 处理转义字符
            if char == '\\' and i + 1 < len(command_str):
                i += 2  # 跳过转义字符和下一个字符
                continue
            
            # 跟踪引号状态
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                i += 1
                continue
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                i += 1
                continue
            
            # 如果不在引号内，检查重定向操作符
            if not in_single_quote and not in_double_quote:
                for op in redirect_operators:
                    op_len = len(op)
                    if i + op_len <= len(command_str):
                        substring = command_str[i:i+op_len]
                        if substring == op:
                            # 找到了重定向操作符
                            # 对于管道符，需要确保不是||（逻辑或）
                            if op == '|':
                                # 检查前后是否是||
                                if ((i > 0 and command_str[i-1] == '|') or 
                                    (i + 1 < len(command_str) and command_str[i+1] == '|')):
                                    i += 1
                                    continue
                            return True
            
            i += 1
        
        return False

    def execute_generic_command(self, input_command):
        """
        统一的命令解析和转译接口
        
        Args:
            input_command: 输入命令，可以是字符串或列表格式
            
        Returns:
            dict: 转译结果
                - success (bool): 是否转译成功
                - translated_command (str): 转译后的命令字符串
                - original_format (str): 原始格式类型 ("string" 或 "list")
                - error (str): 错误信息（如果失败）
        """
        
        try:
            if isinstance(input_command, list): 
                import shlex
                if not input_command:
                    return {
                        "success": False,
                        "error": "Empty command list"
                    }
                
                quoted_parts = []
                for i, part in enumerate(input_command):
                    part_str = str(part)
                    if part_str in ['>', '>>', '<', '|', '&', '&&', '||', ';']:
                        quoted_parts.append(part_str)
                    else:
                        needs_quotes = any(char in part_str for char in [' ', '\t', '\n', '"', "'", '\\', '&', '|', ';', 
                            '(', ')', '<', '>', '$', '`', '*', '?', '[', ']', 
                            '{', '}', '~', '#'])
                        
                        if not needs_quotes: 
                            quoted_parts.append(part_str)
                        else: 
                            if '"' not in part_str:
                                quoted_parts.append(f'"{part_str}"')
                            elif "'" not in part_str:
                                quoted_parts.append(f"'{part_str}'")
                            else:
                                # 如果同时包含单引号和双引号，使用shlex.quote
                                quoted_parts.append(shlex.quote(part_str))
                translated_command = ' '.join(quoted_parts)
                return {
                    "success": True,
                    "translated_command": translated_command,
                    "original_format": "list"
                }
            else:
                # 字符串格式：检查是否是引号包围的重定向命令
                if not input_command.strip():
                    return {
                        "success": False,
                        "error": "Empty command"
                    }
                
                command_str = input_command.strip()
                
                # 检查是否是引号包围的重定向命令（如 'echo "content" > file.txt'）
                if ((command_str.startswith("'") and command_str.endswith("'")) or 
                    (command_str.startswith('"') and command_str.endswith('"'))):
                    
                    # 去掉外层引号
                    inner_command = command_str[1:-1]
                    
                    # 使用智能重定向检测
                    if self.detect_redirection(inner_command):
                        processed_command = inner_command

                        # 处理json内容
                        processed_command = self.process_json(processed_command)
                        marked_command = f"__QUOTED_COMMAND__{processed_command}"
                        
                        
                        return {
                            "success": True,
                            "translated_command": marked_command,
                            "original_format": "string",
                            "is_quoted_redirect": True
                        }
                
                # 基本安全处理：转义反引号防止命令注入
                safe_command = command_str.replace('`', '\\`')
                
                return {
                    "success": True,
                    "translated_command": safe_command,
                    "original_format": "string"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Experimental translation failed: {e}"
            }
    
    def _cleanup_background_tasks(self, command_identifier=None):
        """清理所有已完成的background任务"""
        try:
            current_shell = self.get_current_shell()
            if not current_shell:
                print(f"Error: 没有活跃的shell会话")
                return 1
            
            # 构建清理命令
            cleanup_cmd = f'''
REMOTE_ROOT="{self.REMOTE_ROOT}"
TMP_DIR="$REMOTE_ROOT/tmp"

if [ ! -d "$TMP_DIR" ]; then
    echo "No background tasks to clean up"
    exit 0
fi

CLEANED=0
for result_file in "$TMP_DIR"/cmd_bg_*.result.json; do
    if [ -f "$result_file" ]; then
        BG_PID=$(basename "$result_file" .result.json | sed 's/cmd_bg_//')
        
        # 读取result文件并检查任务状态
        RESULT_DATA=$(cat "$result_file")
        END_TIME=$(echo "$RESULT_DATA" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('end_time', 'Unknown'))" 2>/dev/null || echo "Unknown")
        
        # 如果任务已完成（有end_time），则清理
        if [ "$END_TIME" != "Unknown" ] && [ "$END_TIME" != "null" ] && [ -n "$END_TIME" ]; then
            echo "Cleaning up completed task: $BG_PID"
            rm -f "$TMP_DIR/cmd_bg_${{BG_PID}}".*
            CLEANED=$((CLEANED + 1))
        else
            echo "Skipping running task: $BG_PID"
        fi
    fi
done

echo "Cleaned up $CLEANED completed background tasks"
'''
            
            # 执行清理 - 使用与其他函数相同的方法
            result = self.execute_command_interface("bash", ["-c", cleanup_cmd])
            
            if result.get("success", False):
                # 尝试从不同的数据结构中获取stdout和stderr
                data = result.get("data", {})
                # 优先使用data中的值，只有在data中不存在时才使用result中的值
                stdout = data.get("stdout") if "stdout" in data else result.get("stdout", "")
                stderr = data.get("stderr") if "stderr" in data else result.get("stderr", "")
                stdout = (stdout or "").strip()
                stderr = (stderr or "").strip()
                
                # 统一在命令处理结束后打印输出
                if stdout:
                    print(stdout)
                if stderr:
                    import sys
                    print(stderr, file=sys.stderr)
                return 0
            else:
                error_msg = result.get("error", "Failed to cleanup")
                print(f"Error: {error_msg}")
                return 1
                
        except Exception as e:
            print(f"Error: Cleanup failed: {e}")
            return 1

    def _cleanup_background_task(self, bg_pid, command_identifier=None):
        """清理特定的background任务"""
        try:
            current_shell = self.get_current_shell()
            if not current_shell:
                print(f"Error: 没有活跃的shell会话")
                return 1
            
            # 获取REMOTE_ROOT路径
            tmp_path = f"{self.REMOTE_ROOT}/tmp"
            
            # 构建清理特定任务的命令
            cleanup_cmd = f'''
if [ ! -f "{tmp_path}/cmd_bg_{bg_pid}.result.json" ]; then
    echo "Error: Background task {bg_pid} not found"
    exit 1
fi

# 读取result文件并检查任务状态
RESULT_DATA=$(cat "{tmp_path}/cmd_bg_{bg_pid}.result.json")
END_TIME=$(echo "$RESULT_DATA" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('end_time', 'Unknown'))" 2>/dev/null || echo "Unknown")

# 检查任务是否还在运行
if [ "$END_TIME" = "Unknown" ] || [ "$END_TIME" = "null" ] || [ -z "$END_TIME" ]; then
    echo "Error: Cannot cleanup running task {bg_pid}"
    echo "Wait for the task to complete first"
    exit 1
else
    echo "Cleaning up task: {bg_pid}"
    rm -f "{tmp_path}/cmd_bg_{bg_pid}".*
    echo "Task {bg_pid} cleaned up successfully"
fi
'''
            
            # 生成并执行远程命令
            remote_command, result_filename, cmd_hash = self.command_generator.generate_command(
                cleanup_cmd, None, current_shell
            )
            result = self.command_executor.execute_command(
                remote_command=remote_command,
                result_filename=result_filename,
                cmd_hash=cmd_hash,
                raw_command=cleanup_cmd
            )
            
            if result.get("success", False):
                data = result.get("data", {})
                stdout = data.get("stdout", "").strip()
                stderr = data.get("stderr", "").strip()
                exit_code = data.get("exit_code", 0)
                
                if stdout:
                    print(stdout)
                if stderr:
                    import sys
                    print(stderr, file=sys.stderr)
                
                # 检查shell脚本的退出码
                if exit_code != 0:
                    return 1
                
                return 0
            else:
                error_msg = result.get("error", "Cleanup failed")
                print(f"Error: {error_msg}")
                return 1
                
        except Exception as e:
            print(f"Error: Cleanup failed: {e}")
            return 1

    def _read_background_file(self, bg_pid, file_type, command_identifier=None):
        """通用的后台任务文件读取接口
        
        Args:
            bg_pid: 后台任务ID
            file_type: 文件类型 ('status', 'result', 'log')
            command_identifier: 命令标识符
            
        Returns:
            dict: 包含文件内容的结果字典
        """
        try:
            # 根据文件类型选择相应的文件
            if file_type == 'status':
                from modules.config_loader import get_bg_status_file
                target_file = get_bg_status_file(bg_pid)
            elif file_type == 'result':
                from modules.config_loader import get_bg_result_file
                target_file = get_bg_result_file(bg_pid)
            elif file_type == 'log':
                from modules.config_loader import get_bg_log_file
                target_file = get_bg_log_file(bg_pid)
            else:
                return {"success": False, "error": f"Unknown file type: {file_type}"}
            
            # 使用相对于REMOTE_ROOT的路径（~/开头），而不是绝对路径
            # 这样cmd_cat可以正确解析路径
            file_path = f"~/tmp/{target_file}"
            
            # 使用cmd_cat直接读取文件，避免弹窗
            result = self.cmd_cat(file_path)
            
            if result.get("success", False):
                # 将cmd_cat的结果转换为统一格式
                content = result.get("output", "")
                # 检查内容是否为空，空内容可能意味着文件不存在
                if not content.strip():
                    return {"success": False, "error": f"File {file_path} is empty or not found"}
                return {
                    "success": True,
                    "data": {
                        "stdout": content,
                        "stderr": ""
                    }
                }
            else:
                return {"success": False, "error": result.get("error", "Failed to read file")}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _show_background_result(self, bg_pid, command_identifier=None):
        """显示background任务的最终结果 - 先检查状态，再读取结果"""
        try:
            # 从result文件读取状态和结果信息
            result = self._read_background_file(bg_pid, 'result', command_identifier)
            
            # 处理统一接口的结果
            if result.get("success", False):
                data = result.get("data", {})
                result_content = data.get("stdout", "").strip()
                
                if result_content:
                    try:
                        import json
                        # 解析result文件的JSON内容
                        result_json = json.loads(result_content)
                        
                        status = result_json.get("status", "unknown")
                        
                        # 如果任务还在运行，提示用户
                        if status == "running":
                            print(f"Task {bg_pid} is still running.")
                            print(f"Use 'GDS --bg --status {bg_pid}' to check current status")
                            print(f"Use 'GDS --bg --log {bg_pid}' to view current output")
                            return 1
                        elif status != "completed":
                            print(f"Task {bg_pid} has status: {status}")
                            return 1
                        
                        # 任务已完成，显示输出
                        stdout_content = result_json.get("stdout", "")
                        stderr_content = result_json.get("stderr", "")
                        exit_code = result_json.get("exit_code", 0)
                        
                        # 显示后台任务的输出
                        if stdout_content:
                            print(stdout_content, end="")
                        
                        if stderr_content:
                            import sys
                            print(stderr_content, file=sys.stderr, end="")
                        
                        return exit_code
                        
                    except json.JSONDecodeError as e:
                        print(f"Error: Invalid JSON in result file: {e}")
                        return 1
                else:
                    # 检查stderr中是否有"No such file"错误
                    if "no such file" in stderr.lower() or "not found" in stderr.lower():
                        print(f"Error: Background task {bg_pid} result file not found")
                        print(f"This usually means the task failed to complete or the result file was not created")
                        print(f"Use 'GDS --bg --status {bg_pid}' to check task status")
                        print(f"Use 'GDS --bg --log {bg_pid}' to check task logs")
                    else:
                        print(f"Error: Empty result file for task {bg_pid}")
                    return 1
                    
            else:
                # 检查stderr中是否有"No such file"错误
                data = result.get("data", {})
                stderr = data.get("stderr", "")
                if "no such file" in stderr.lower() or "not found" in stderr.lower():
                    print(f"Error: Background task {bg_pid} result file not found")
                    print(f"This usually means the task failed to complete or the result file was not created")
                    print(f"Use 'GDS --bg --status {bg_pid}' to check task status")
                    print(f"Use 'GDS --bg --log {bg_pid}' to check task logs")
                else:
                    error_msg = result.get("error", "Failed to read result file")
                    print(f"Error: {error_msg}")
                return 1
                
        except Exception as e:
            print(f"Error: Result view failed: {e}")
            return 1
    
    def check_and_setup_mount_point(self):
        """检查并设置动态挂载点"""
        import os
        import tempfile
        
        # 使用临时文件存储当前session的挂载点信息
        self.mount_info_file = os.path.join(tempfile.gettempdir(), "gds_current_mount.txt")
        
        # 检查是否有现有的挂载点
        if os.path.exists(self.mount_info_file):
            try:
                with open(self.mount_info_file, 'r') as f:
                    stored_mount_point = f.read().strip()
                if stored_mount_point:
                    # 验证挂载点的指纹文件（静默模式，不输出调试信息）
                    if self.verify_mount_fingerprint(stored_mount_point, silent=True):
                        self.current_mount_point = stored_mount_point
                        self._update_paths_for_dynamic_mount(stored_mount_point)
                        return
            except Exception as e:
                print(f"Warning: 读取挂载点信息失败: {e}")
        
        try: 
            from modules.config_loader import get_config
            config = get_config()
            default_remote_root = config.REMOTE_ROOT
            if self.REMOTE_ROOT == default_remote_root:
                self.dynamic_mode = True
            else:
                self.dynamic_mode = False
                
        except Exception as e:
            self.dynamic_mode = False
    
    def _update_paths_for_dynamic_mount(self, mount_point):
        """更新路径以使用动态挂载点"""
        self.current_mount_point = mount_point
        self.dynamic_mode = True
        
        # 保存挂载点信息到临时文件
        try:
            import os
            import tempfile
            mount_info_file = os.path.join(tempfile.gettempdir(), "gds_current_mount.txt")
            with open(mount_info_file, 'w') as f:
                f.write(mount_point)
        except Exception as e:
            print(f"Warning: 保存挂载点信息失败: {e}")
    
    def verify_mount_fingerprint(self, mount_point, silent=False):
        """验证挂载点的指纹文件（通过Google Drive API）"""
        import json
        
        try:
            # 首先确保我们有Google Drive API服务
            if not self.drive_service:
                return False
            
            if not hasattr(self, 'REMOTE_ROOT_FOLDER_ID'):
                return False
            
            # 首先获取tmp文件夹ID
            # 注意: list_files不支持query参数，需要手动过滤
            tmp_folder_result = self.drive_service.list_files(
                folder_id=self.REMOTE_ROOT_FOLDER_ID, 
                max_results=100  # 获取足够多的结果以便过滤
            )
            
            if not tmp_folder_result.get('success') or not tmp_folder_result.get('files'):
                return False
            
            # 过滤出名为'tmp'的文件夹
            tmp_folder = None
            for item in tmp_folder_result['files']:
                if item.get('name') == 'tmp' and item.get('mimeType') == 'application/vnd.google-apps.folder':
                    tmp_folder = item
                    break
            
            if not tmp_folder:
                return False
            
            tmp_folder_id = tmp_folder['id']
            
            # 列出tmp文件夹中的所有文件
            result = self.drive_service.list_files(folder_id=tmp_folder_id, max_results=100)
            if not result.get('success'):
                if not silent:
                    print(f"Error: 无法访问tmp文件夹: {result.get('error', '未知错误')}")
                return False
            files = result.get('files', [])
            
            # 查找指纹文件
            fingerprint_files = [f for f in files if f['name'].startswith('.gds_mount_fingerprint_')]
            
            if not fingerprint_files:
                return False
            
            # 使用最新的指纹文件（按名称排序，最新的在最后）
            latest_fingerprint = max(fingerprint_files, key=lambda x: x['name'])
            
            # 下载并读取指纹文件内容（使用临时文件）
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                download_result = self.drive_service.download_file(latest_fingerprint['id'], temp_path)
                if not download_result.get('success'):
                    if not silent:
                        print(f"Error: 无法下载指纹文件: {download_result.get('error', '未知错误')}")
                    return False
                
                # 读取临时文件内容
                with open(temp_path, 'r', encoding='utf-8') as f:
                    fingerprint_content = f.read()
                
                # 解析指纹文件内容
                try:
                    fingerprint_data = json.loads(fingerprint_content)
                except json.JSONDecodeError as e:
                    if not silent:
                        print(f"Error: 指纹文件JSON格式错误: {e}")
                    return False
                    
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            # 验证指纹数据的基本结构
            required_fields = ["mount_point", "timestamp", "hash", "signature", "type"]
            for field in required_fields:
                if field not in fingerprint_data:
                    if not silent:
                        print(f"Error: 指纹文件缺少必需字段: {field}")
                    return False
            
            # 验证挂载点匹配
            if fingerprint_data.get("mount_point") != mount_point:
                if not silent:
                    print(f"Error: 挂载点不匹配: 期望 {mount_point}, 实际 {fingerprint_data.get('mount_point')}")
                return False
            
            # 验证文件类型
            if fingerprint_data.get("type") != "mount_fingerprint":
                if not silent:
                    print(f"Error: 指纹文件类型不正确: {fingerprint_data.get('type')}")
                return False
            
            # 验证签名格式（基本验证）
            signature = fingerprint_data.get("signature", "")
            expected_prefix = f"{fingerprint_data.get('timestamp')}_{fingerprint_data.get('hash')}_"
            if not signature.startswith(expected_prefix):
                if not silent:
                    print(f"Error: 指纹签名格式不正确")
                return False
            
            # 验证通过，更新本地配置中的文件夹ID
            remote_root_id = fingerprint_data.get("remote_root_id")
            remote_env_id = fingerprint_data.get("remote_env_id")
            
            if remote_root_id:
                self.REMOTE_ROOT_FOLDER_ID = remote_root_id
            
            if remote_env_id:
                self.REMOTE_ENV_FOLDER_ID = remote_env_id
            
            # 保存folder ID到config.json
            self._save_folder_ids_to_config(remote_root_id, remote_env_id)
            
            return True
            
        except Exception as e:
            if not silent:
                print(f"Error: 指纹验证失败: {e}")
            return False
        
    def _save_folder_ids_to_config(self, remote_root_id=None, remote_env_id=None):
        """保存folder ID到config.json"""
        try:
            import json
            import os
            
            # GOOGLE_DRIVE_DATA路径
            try:
                from .modules.path_constants import get_data_dir
                config_file = str(get_data_dir() / "config.json")
            except ImportError:
                config_file = os.path.expanduser("~/.local/bin/GOOGLE_DRIVE_DATA/config.json")
            
            # 读取现有配置
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {"version": "1.0.0", "constants": {}}
            
            # 更新constants
            if "constants" not in config:
                config["constants"] = {}
            
            if remote_root_id:
                config["constants"]["REMOTE_ROOT_FOLDER_ID"] = remote_root_id
            
            if remote_env_id:
                config["constants"]["REMOTE_ENV_FOLDER_ID"] = remote_env_id
            
            # 保存配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
        except Exception as e:
            print(f"Warning: 保存folder ID到config.json失败: {e}")
    
    def load_paths_from_config(self):
        """从config.json动态加载REMOTE_ROOT和REMOTE_ENV路径"""
        try:
            import json
            import os
            
            # GOOGLE_DRIVE_DATA路径 - 使用统一路径常量
            try:
                from .modules.path_constants import get_data_dir
                config_dir = str(get_data_dir())
                config_file = str(get_data_dir() / "config.json")
            except ImportError:
                config_dir = os.path.expanduser("~/.local/bin/GOOGLE_DRIVE_DATA")
                config_file = os.path.join(config_dir, "config.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 从配置中读取路径
                constants = config.get('constants', {})
                
                # 如果配置中有动态路径，使用它们
                if 'REMOTE_ROOT' in constants:
                    self.REMOTE_ROOT = constants['REMOTE_ROOT']
                
                if 'REMOTE_ENV' in constants:
                    self.REMOTE_ENV = constants['REMOTE_ENV']
                
                if 'REMOTE_ROOT_FOLDER_ID' in constants:
                    self.REMOTE_ROOT_FOLDER_ID = constants['REMOTE_ROOT_FOLDER_ID']
                
                if 'REMOTE_ENV_FOLDER_ID' in constants:
                    self.REMOTE_ENV_FOLDER_ID = constants['REMOTE_ENV_FOLDER_ID']
                
                # 如果有当前挂载点信息，更新它
                if 'CURRENT_MOUNT_POINT' in constants:
                    self.current_mount_point = constants['CURRENT_MOUNT_POINT']
                    self.dynamic_mode = constants.get('MOUNT_TYPE') == 'dynamic'
                
                # 加载挂载哈希值
                if 'MOUNT_HASH' in constants:
                    self.MOUNT_HASH = constants['MOUNT_HASH']
                
                # 加载挂载时间戳
                if 'MOUNT_TIMESTAMP' in constants:
                    self.MOUNT_TIMESTAMP = constants['MOUNT_TIMESTAMP']
                
            else:
                print("Warning: config.json不存在，使用默认路径")
                
        except Exception as e:
            print(f"ERROR: 从config.json加载路径失败: {e}")
            print("使用默认路径")
    
    def handle_command_line_args(self, args=None, command_identifier=None):
        """
        处理命令行参数 - 替代remote_commands.main()的功能
        
        Args:
            args: 命令行参数列表，如果为None则从sys.argv获取
            command_identifier: 命令标识符
            
        Returns:
            int: 退出码
        """
        import sys
        
        if args is None:
            # 检查是否在RUN环境中
            if len(sys.argv) > 1 and (sys.argv[1].startswith('test_') or sys.argv[1].startswith('cmd_')):
                command_identifier = sys.argv[1]
                args = sys.argv[2:]
            else:
                args = sys.argv[1:]
        
        # 导入需要的函数
        from modules.help_system import show_unified_help
        
        if not args:
            # 默认显示帮助
            show_unified_help()
            return 0
        
        # 处理各种命令行参数
        if args[0] in ['--help', '-h']:
            show_unified_help()
            return 0
        elif args[0] == '--console-setup':
            # TODO: 实现console_setup_interactive
            print("Console setup not implemented yet")
            return 1
        elif args[0] == '--create-remote-shell':
            return self.create_shell(None, None, command_identifier)
        elif args[0] == '--list-remote-shell':
            return self.list_shells(command_identifier)
        elif args[0] == '--checkout-remote-shell':
            if len(args) < 2:
                print(f"Error: 需要指定shell ID")
                return 1
            shell_id = args[1]
            return self.checkout_shell(shell_id, command_identifier)
        elif args[0] == '--terminate-remote-shell':
            if len(args) < 2:
                print(f"Error: 需要指定shell ID")
                return 1
            shell_id = args[1]
            return self.terminate_shell(shell_id, command_identifier)
        elif args[0] == '--remount':
            # 处理重新挂载命令
            return self.handle_remount_command(command_identifier)
        elif args[0] == '--shell':
            # 检查是否有flags
            has_no_direct_feedback = '--no-direct-feedback' in args
            filtered_args = [arg for arg in args[1:] if arg not in ['--no-direct-feedback', '--priority']]
            
            if not filtered_args:
                # 没有命令参数，进入交互模式
                from .modules.shell_commands import enter_shell_mode
                # 设置flags
                if has_no_direct_feedback and hasattr(self, 'command_executor'):
                    self.command_executor._no_direct_feedback = True
                return enter_shell_mode(command_identifier)
            else:
                # 执行指定的shell命令
                return self.handle_shell_command_args(args[1:], command_identifier)
        elif args[0] == '--desktop':
            return self.handle_desktop_command(args[1:], command_identifier)
        else:
            # 未知参数
            print(f"Error: Unknown argument '{args[0]}'")
            print("Use --help for usage information")
            return 1
    
    def handle_shell_command_args(self, shell_cmd_parts, command_identifier=None):
        """处理--shell命令的参数"""
        no_direct_feedback = False
        is_priority = False
        filtered_shell_parts = []
        
        for part in shell_cmd_parts:
            if part == '--no-direct-feedback':
                no_direct_feedback = True
            elif part == '--priority':
                is_priority = True
            else:
                filtered_shell_parts.append(part)
        
        shell_cmd_parts = filtered_shell_parts
        
        # 如果没有命令参数，说明是空命令，返回0（成功）
        if not shell_cmd_parts:
            return 0
        
        # 检测引号包围的完整命令（用于远端重定向等）
        if len(shell_cmd_parts) == 1 and (' > ' in shell_cmd_parts[0] or ' && ' in shell_cmd_parts[0] or ' || ' in shell_cmd_parts[0] or ' | ' in shell_cmd_parts[0]):
            # 这是一个引号包围的完整命令，直接使用
            shell_cmd = shell_cmd_parts[0]
            # 只有在没有标记的情况下才添加标记，避免重复添加
            if not shell_cmd.startswith("__QUOTED_COMMAND__"):
                shell_cmd = f"__QUOTED_COMMAND__{shell_cmd}"
        else:
            # 正常的多参数命令，需要正确处理带空格的参数
            # 对包含空格的参数添加引号
            shell_cmd_parts_quoted = []
            for part in shell_cmd_parts:
                if ' ' in part:
                    shell_cmd_parts_quoted.append(f'"{part}"')
                else:
                    shell_cmd_parts_quoted.append(part)
            shell_cmd = ' '.join(shell_cmd_parts_quoted)
        
        # 设置模式标志
        if no_direct_feedback and hasattr(self, 'command_executor'):
            self.command_executor._no_direct_feedback = True
        
        if is_priority and hasattr(self, 'command_executor'):
            self.command_executor._is_priority = True
        
        # 执行shell命令
        return self.execute_shell_command(shell_cmd, command_identifier)
    
    def handle_desktop_command(self, args, command_identifier=None):
        """处理--desktop命令"""
        if not args:
            print(f"Error: --desktop needs to specify operation type")
            return 1
        
        desktop_action = args[0]
        if desktop_action == '--status':
            try:
                from .modules.sync_config_manager import get_google_drive_status
                return get_google_drive_status(command_identifier)
            except ImportError:
                try:
                    from modules.sync_config_manager import get_google_drive_status
                    return get_google_drive_status(command_identifier)
                except ImportError:
                    print(f"Error: Unable to find get_google_drive_status function")
                    return 1
        elif desktop_action == '--shutdown':
            try:
                from .modules.drive_process_manager import shutdown_google_drive
                return shutdown_google_drive(command_identifier)
            except ImportError:
                try:
                    from modules.drive_process_manager import shutdown_google_drive
                    return shutdown_google_drive(command_identifier)
                except ImportError:
                    print(f"Error: Unable to find shutdown_google_drive function")
                    return 1
        else:
            print(f"Error: Unknown desktop action '{desktop_action}'")
            return 1
    
    def handle_remount_command(self, command_identifier=None):
        """处理python: GOOGLE_DRIVE --remount命令"""
        from modules.remount_manager import remount_google_drive
        return remount_google_drive(command_identifier)
    