"""
Google Drive Shell - Navigation Command Module

This module provides directory navigation functionality for the Google Drive Shell system.
It implements the fundamental navigation commands 'cd' and 'pwd' with support for various
path formats and shell state management.

Key Features:
- Directory changing with comprehensive path resolution
- Current directory display with logical path formatting
- Support for multiple path formats (~, @, relative, absolute)
- Shell state persistence across navigation operations
- Integration with Google Drive folder structure
- Proper error handling for invalid paths and access issues

Commands:
- cd <path>: Change to specified directory
- cd: Change to home directory (~)
- cd ..: Change to parent directory
- pwd: Display current working directory

Path Support:
- Logical paths: ~/documents, @/python
- Relative paths: ../folder, ./file
- Absolute paths: /full/path/to/directory
- Special directories: ., .., ~, @

Navigation Flow:
1. Parse and validate target path
2. Resolve path using path resolver
3. Verify directory exists and is accessible
4. Update shell state with new current directory
5. Persist navigation state for future sessions

Classes:
    NavigationCommand: Main navigation command handler

Dependencies:
    - Path resolution for directory mapping
    - Shell state management for current directory tracking
    - Google Drive API for directory validation
    - Remote command execution for path operations

Migrated from: file_core.py (combined cd_command and pwd_command)
"""

import time
from .base_command import BaseCommand


class NavigationCommand(BaseCommand):
    """导航命令 - 统一处理pwd, cd"""
    
    @property
    def command_name(self):
        # 返回主命令名，但这个类会注册多个命令
        return "navigation"
    
    
    def execute(self, cmd, args, command_identifier=None):
        """根据命令名分发到具体的处理方法"""
        if cmd == "pwd":
            return self.execute_pwd(args)
        elif cmd == "cd":
            return self.execute_cd(args)
        else:
            print(f"Error: Unknown navigation command: {cmd}")
            return 1
    
    def execute_pwd(self, args):
        """执行pwd命令"""
        # 检查是否请求帮助
        if args and (args[0] == '--help' or args[0] == '-h'):
            self.show_pwd_help()
            return 0
        
        # 检查是否有-id参数
        if args and len(args) >= 2 and args[0] == '-id':
            folder_id = args[1]
            return self.resolve_id_to_path(folder_id)
        
        # pwd命令不需要参数
        if args:
            print("pwd: too many arguments")
            return 1
        
        result = self.cmd_pwd()
        
        if result.get("success", False):
            print(result.get("current_path", "~"))
            return 0
        else:
            print(result.get("error", "Failed to get current directory"))
            return 1
    
    def execute_cd(self, args):
        """执行cd命令"""
        # 检查是否请求帮助
        if args and (args[0] == '--help' or args[0] == '-h'):
            self.show_cd_help()
            return 0
        
        if not args:
            # cd without arguments should go to home directory
            path = "~"
        else:
            path = args[0]
            # If path is empty string, let remote bash handle it
            if path == "":
                # Pass empty string to remote for bash to handle
                return self.main_instance.execute_remote_command(f'cd ""')
        
        # 调用shell的cd方法
        result = self.cmd_cd(path)
        
        if result.get("success", False):
            if not result.get("direct_feedback", False):
                if (result.get("output", "")): 
                    print(result.get("output", ""))
            return 0
        else:
            print(result.get("error", "Failed to change directory"))
            return 1

    def cmd_pwd(self):
        """显示当前路径"""
        current_shell = self.main_instance.get_current_shell()
        if not current_shell:
            return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
        
        return {
            "success": True,
            "current_path": current_shell.get("current_path", "~"),
            "home_url": self.main_instance.HOME_URL,
            "shell_id": current_shell["id"],
            "shell_name": current_shell["name"]
        }
    
    def cmd_cd(self, path):
        """切换目录"""
        current_shell = self.main_instance.get_current_shell()
        if not current_shell:
            return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
        
        if not path:
            path = "~"
            
        # 应用本地路径转换（将bash展开的本地路径转换回远程路径格式）
        path = self.main_instance.path_resolver.undo_local_path_user_expansion(path)
        
        # 规范化路径，处理../等相对路径组件
        normalized_path = self.main_instance.path_resolver.resolve_remote_absolute_path(path, current_shell, return_logical=True)
        
        # 检查路径是否有效
        if normalized_path is None:
            return {"success": False, "error": f"bash: cd: {path}: No such file or directory"}
            
        # cd命令需要逻辑路径格式，需要将绝对路径转换回逻辑路径
        # 但只对cd命令进行这种转换
        if normalized_path.startswith('/content/drive/MyDrive/REMOTE_ROOT'):
            # 转换绝对路径为逻辑路径
            relative_part = normalized_path[len('/content/drive/MyDrive/REMOTE_ROOT'):]
            if relative_part.startswith('/'):
                relative_part = relative_part[1:]
            absolute_path = f"~/{relative_part}" if relative_part else "~"
        elif normalized_path.startswith('/content/drive/MyDrive/REMOTE_ENV'):
            # @路径转换
            relative_part = normalized_path[len('/content/drive/MyDrive/REMOTE_ENV'):]
            if relative_part.startswith('/'):
                relative_part = relative_part[1:]
            absolute_path = f"@/{relative_part}" if relative_part else "@"
        else:
            # 其他情况直接使用规范化后的路径
            absolute_path = normalized_path
        
        # 使用统一的cmd_ls接口检测目录是否存在
        ls_result = self.main_instance.cmd_ls(absolute_path)
        
        if not ls_result.get('success'):
            # 目录不存在，将ls错误格式转换为cd格式
            from ..error_handler import EnhancedErrorHandler
            ls_result = EnhancedErrorHandler.convert_ls_error_to_command_format(ls_result, 'cd')
            return ls_result
        
        # 如果ls成功，说明目录存在，使用resolve_drive_id获取目标ID和路径
        # 使用规范化后的绝对路径进行解析
        target_id, target_path = self.main_instance.resolve_drive_id(absolute_path, current_shell)
        if not target_id:
            return {"success": False, "error": f"bash: cd: {path}: No such file or directory"}
        
        # 更新shell状态
        shells_data = self.main_instance.load_shells()
        shell_id = current_shell['id']
        
        shells_data["shells"][shell_id]["current_path"] = target_path
        shells_data["shells"][shell_id]["current_folder_id"] = target_id
        shells_data["shells"][shell_id]["last_accessed"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        if self.main_instance.save_shells(shells_data):
            return {
                "success": True,
                "new_path": target_path,
                "folder_id": target_id,
                "message": f"Switched to directory: {target_path}"
            }
        else:
            return {"success": False, "error": "Save shell state failed"}
    
    def show_pwd_help(self):
        """显示pwd命令的帮助信息"""
        help_text = """pwd - print working directory

Usage:
  pwd [options]

Options:
  -h, --help               Show this help message

Description:
  Display the current working directory path in Google Drive.
  Returns the logical path in the format ~/path/to/directory.

Examples:
  pwd                      Display current directory
"""
        print(help_text)
    
    def show_cd_help(self):
        """显示cd命令的帮助信息"""
        help_text = """cd - change directory

Usage:
  cd <directory> [options]

Arguments:
  directory                Target directory path (absolute or relative)

Options:
  -h, --help               Show this help message

Description:
  Change the current working directory to the specified path.
  Supports both absolute paths (~/...) and relative paths (./..., ../).
  The directory must exist in Google Drive.

Examples:
  cd ~/Documents           Change to Documents folder
  cd ../                   Move up one directory level
  cd ./subfolder           Change to subfolder in current directory
  cd ~                     Change to home directory (REMOTE_ROOT)
"""
        print(help_text)
    
    def resolve_id_to_path(self, folder_id):
        """
        将Google Drive ID解析为逻辑路径
        使用cached id file逐层逆推直到遇到第一个已知parent
        """
        try:
            # 获取drive service
            drive_service = self.main_instance.drive_service
            if not drive_service:
                print("Error: Google Drive service not available")
                return 1
            
            # 构建路径的递归函数
            def build_path_from_id(file_id, visited=None):
                if visited is None:
                    visited = set()
                
                # 防止循环引用
                if file_id in visited:
                    return None, "Circular reference detected"
                visited.add(file_id)
                
                try:
                    # 获取文件/文件夹信息
                    file_info = drive_service.service.files().get(
                        fileId=file_id, 
                        fields='id,name,parents,mimeType'
                    ).execute()
                    
                    file_name = file_info.get('name', '')
                    parents = file_info.get('parents', [])
                    mime_type = file_info.get('mimeType', '')
                    
                    # 检查是否是文件夹
                    if mime_type != 'application/vnd.google-apps.folder':
                        return None, f"ID {file_id} is not a folder"
                    
                    # 如果没有父文件夹，说明是根目录
                    if not parents:
                        return file_name, None
                    
                    parent_id = parents[0]
                    
                    # 检查是否是已知的根目录
                    if parent_id == self.main_instance.REMOTE_ROOT_FOLDER_ID:
                        return f"~/{file_name}", None
                    elif parent_id == self.main_instance.REMOTE_ENV_FOLDER_ID:
                        return f"@/{file_name}", None
                    
                    # 递归获取父路径
                    parent_path, error = build_path_from_id(parent_id, visited.copy())
                    if error:
                        return None, error
                    
                    if parent_path is None:
                        return None, f"Cannot resolve parent path for ID {parent_id}"
                    
                    # 构建完整路径
                    if parent_path == "~":
                        return f"~/{file_name}", None
                    elif parent_path == "@":
                        return f"@/{file_name}", None
                    else:
                        return f"{parent_path}/{file_name}", None
                        
                except Exception as e:
                    return None, f"Failed to get info for ID {file_id}: {str(e)}"
            
            # 开始解析
            path, error = build_path_from_id(folder_id)
            
            if error:
                print(f"Error: {error}")
                return 1
            
            if path is None:
                print(f"Error: Unknown path for ID {folder_id}")
                return 1
            
            print(path)
            return 0
            
        except Exception as e:
            print(f"Error: Failed to resolve ID {folder_id}: {str(e)}")
            return 1
