"""
Google Drive Shell - Ls Command Module

This module provides directory listing functionality for the Google Drive Shell system.
It implements the 'ls' command with support for various options and formats, similar to
the traditional Unix ls command but adapted for the Google Drive environment.

Key Features:
- Directory and file listing with detailed information
- Support for various ls options (-l, -a, -h, etc.)
- Integration with Google Drive API for metadata
- Path resolution for both logical and absolute paths
- Formatted output with file sizes, permissions, and timestamps
- Error handling for non-existent paths and access issues

Commands:
- ls: List current directory contents
- ls <path>: List specified directory contents
- ls -l: Long format with detailed information
- ls -a: Show hidden files and directories
- ls -h: Human-readable file sizes

Output Formats:
- Simple listing: filename per line
- Long format: permissions, size, date, name
- Detailed metadata: includes Google Drive specific information

Classes:
    LsCommand: Main ls command handler with comprehensive listing functionality

Dependencies:
    - Google Drive API for file metadata
    - Path resolution for directory navigation
    - Remote command execution for file system operations
    - JSON processing for structured data handling
"""

from .base_command import BaseCommand
from ..result_processor import ResultProcessor
import json
import os

class LsCommand(BaseCommand):
    @property
    def command_name(self):
        return "ls"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行ls命令"""
        # 检查是否请求帮助
        if '--help' in args or '-h' in args:
            self.show_help()
            return 0
        
        # 解析参数
        detailed = False
        recursive = False
        force_remote = False  # -f标志，使用远程bash强制刷新
        show_hidden = False  # -a标志，显示隐藏文件
        path = None
        folder_id = None  # --id参数指定的文件夹ID
        has_bash_flags = False
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == '--detailed' or arg == '-l':
                detailed = True
            elif arg == '-R':
                recursive = True
            elif arg == '-f' or arg == '--force':
                force_remote = True
            elif arg == '-a' or arg == '--all':
                show_hidden = True
            elif arg == '--id':
                # 下一个参数应该是文件夹ID
                if i + 1 < len(args):
                    folder_id = args[i + 1]
                    i += 1  # 跳过ID参数
                else:
                    print("Error: --id requires a folder ID argument")
                    return 1
            elif arg.startswith('-'):
                has_bash_flags = True
                break
            else:
                path = arg
            i += 1
        
        # 如果有bash flags，作为远端命令执行
        if has_bash_flags:
            full_command = 'ls ' + ' '.join(args)
            result = self.shell.execute_command_interface('bash', ['-c', full_command])
            import traceback
            if result.get('success'):
                data = result.get('data', {})
                stdout = data.get('stdout', '')
                if stdout:
                    print(stdout, end='')
                return 0
            else:
                data = result.get('data', {})
                error = result.get('error', data.get('stderr', f'Command failed. Call stack: {traceback.format_exc()}'))
                print(error)
                return 1
        
        # 如果指定了--id，验证参数冲突
        if folder_id:
            if path:
                print("Error: Cannot specify both path and --id. Use either path or --id, not both.")
                return 1
            if force_remote:
                print("Error: --id cannot be used with --force (-f). --id uses Google Drive API directly.")
                return 1
        
        # 检查是否包含通配符
        if path and ('*' in path or '?' in path or '[' in path):
            return self.shell.handle_wildcard_ls(path)
        
        # 如果指定了--id，直接使用文件夹ID进行列表
        if folder_id:
            result = self.shell.cmd_ls_by_id(folder_id, detailed=detailed, recursive=recursive, show_hidden=show_hidden)
        elif force_remote:
            # 如果有-f标志，直接调用cmd_ls_remote（远程bash）
            result = self.shell.cmd_ls_remote(path, detailed=detailed, recursive=recursive, show_hidden=show_hidden)
        else:
            # 调用shell的ls方法（使用Google Drive API）
            result = self.shell.cmd_ls(path, detailed=detailed, recursive=recursive, show_hidden=show_hidden)
        
        if result.get("success", False):
            files = result.get("files", [])
            folders = result.get("folders", [])
            all_items = folders + files
            
            if all_items:
                # 按名称排序，文件夹优先
                sorted_folders = sorted(folders, key=lambda x: x.get('name', '').lower())
                sorted_files = sorted(files, key=lambda x: x.get('name', '').lower())
                
                # 合并列表，文件夹在前
                all_sorted_items = sorted_folders + sorted_files
                
                if detailed:
                    # 详细模式：显示表格化信息，类似 ls -la
                    self.print_detailed_listing(all_sorted_items)
                else:
                    # 简单的列表格式，类似bash ls
                    for item in all_sorted_items:
                        name = item.get('name', 'Unknown')
                        if item.get('mimeType') == 'application/vnd.google-apps.folder':
                            print(f"{name}/")
                        else:
                            print(name)
            
            return 0
        else:
            print(result.get("error", "Failed to list directory"))
            return 1


    def convert_absolute_to_logical(self, path):
        """
        内部接口：将远端绝对路径转换为逻辑路径
        
        Args:
            path (str): 可能是逻辑路径或远端绝对路径
            
        Returns:
            str: 逻辑路径格式 (~/xxx)
        """
        if not path:
            return path
        
        # 如果已经是逻辑路径格式（~/xxx 或 @drive_equivalent/xxx），直接返回
        if path.startswith("~/") or path == "~" or path.startswith("@drive_equivalent"):
            return path
        
        # 如果是相对路径（不以/开头），直接返回
        if not path.startswith("/"):
            return path
        
        # 路径已经在execute_shell_command中统一处理，无需重复处理
        
        # 如果转换后已经是~/格式，直接返回
        if path.startswith("~/") or path == "~":
            return path
        
        # 检查是否是远端绝对路径
        remote_root = self.main_instance.REMOTE_ROOT
        if path.startswith(remote_root):
            # 去掉REMOTE_ROOT前缀，转换为~/xxx格式
            relative_part = path[len(remote_root):]
            if relative_part.startswith("/"):
                relative_part = relative_part[1:]
            
            if relative_part:
                return f"~/{relative_part}"
            else:
                return "~"
        
        # 检查是否是REMOTE_ENV路径
        remote_env = self.main_instance.REMOTE_ENV
        if path.startswith(remote_env):
            # 去掉REMOTE_ENV前缀，转换为@/xxx格式
            relative_part = path[len(remote_env):]
            if relative_part.startswith("/"):
                relative_part = relative_part[1:]
            
            if relative_part:
                return f"@/{relative_part}"
            else:
                return "@"
        
        # 如果是其他格式的绝对路径，假设它是REMOTE_ROOT的子路径
        # 例如 /tmp/file.txt -> ~/tmp/file.txt
        if path.startswith("/"):
            return f"~/{path[1:]}"  # 正确：移除前导/，然后添加~/
        
        # 默认返回原路径
        return path
    
    def get_configured_folder_id(self, logical_path):
        """从配置文件获取指定逻辑路径的folder ID"""
        try:
            from ..path_constants import PathConstants
            path_constants = PathConstants()
            config_path = str(path_constants.GDS_PATH_IDS_FILE)
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                return config.get("path_ids", {}).get(logical_path)
            return None
        except Exception:
            return None
    
    def find_nearest_parent_id(self, logical_path):
        """找到最近的父目录ID，用于智能路径解析"""
        try:
            try:
                from ..path_constants import PathConstants
                path_constants = PathConstants()
                config_path = str(path_constants.GDS_PATH_IDS_FILE)
            except ImportError:
                # 回退到旧路径（向后兼容）
                config_path = os.path.expanduser("~/.gds_path_ids.json")
            if not os.path.exists(config_path):
                return None, None
                
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            path_ids = config.get("path_ids", {})
            
            # 如果直接有这个路径的ID，返回它（精确匹配优先）
            if logical_path in path_ids:
                return path_ids[logical_path], logical_path
            
            # 找到最长匹配的父路径
            best_match = None
            best_match_path = None
            
            for config_path_key, folder_id in path_ids.items():
                # 检查是否是父路径（必须是真正的父路径，不是自己）
                if logical_path.startswith(config_path_key + "/"):
                    # 找到更长的匹配（更接近的父目录）
                    if best_match is None or len(config_path_key) > len(best_match_path):
                        best_match = folder_id
                        best_match_path = config_path_key
            
            return best_match, best_match_path
            
        except Exception as e:
            print(f"Warning: Failed to find nearest parent ID: {e}")
            return None, None
    
    def _resolve_from_parent_id(self, target_path, parent_id, parent_path):
        """从配置的父目录ID解析到目标路径"""
        try:
            # 计算相对路径
            if not target_path.startswith(parent_path + "/"):
                return None, None
            
            relative_path = target_path[len(parent_path) + 1:]  # 去掉父路径和"/"
            path_parts = relative_path.split("/")
            
            current_id = parent_id
            current_path = parent_path
            
            # 逐级解析路径
            for i, part in enumerate(path_parts):
                if not part:  # 跳过空部分
                    continue
                
                # 查找子文件夹
                result = self.drive_service.list_files(folder_id=current_id, max_results=100)
                
                if not result['success']:
                    # 使用统一的错误信息模板
                    result_processor = ResultProcessor(self.shell)
                    base_error = f"Unable to find the id for subfolder '{part}' from the current folder '{current_path}' (id: {current_id})"
                    api_error = result.get('error', 'API access failed')
                    if api_error != 'API access failed':
                        base_error += f". \n\nAPI error: {api_error}"
                    error_msg = result_processor._format_timeout_error_with_solutions(base_error, f"{current_path}/{part}", current_id)
                    return None, error_msg
                
                found_folder = None
                found_file = None
                
                # 查找匹配的文件夹或文件
                for file in result['files']:
                    if file['name'] == part:
                        if file['mimeType'] == 'application/vnd.google-apps.folder':
                            found_folder = file
                        else:
                            found_file = file
                        break
                
                # 如果这是最后一个路径组件，可能是文件
                is_last_component = (i == len(path_parts) - 1)
                
                if found_folder:
                    # 找到文件夹，继续解析
                    current_id = found_folder['id']
                    current_path = f"{current_path}/{part}"
                elif found_file and is_last_component:
                    # 最后一个组件是文件，返回父目录ID（用于ls文件）
                    return current_id, current_path
                else:
                    # 没找到匹配项 - 使用统一的错误信息模板
                    result_processor = ResultProcessor(self.shell)
                    if is_last_component:
                        base_error = f"Unknown error: Unable to find the id for file or subfolder '{part}' from the current folder '{current_path}' (id: {current_id})"
                    else:
                        base_error = f"Unknown error: Unable to find the id for subfolder '{part}' from the current folder '{current_path}' (id: {current_id})"
                    error_msg = result_processor._format_timeout_error_with_solutions(base_error, f"{current_path}/{part}", current_id)
                    return None, error_msg
            
            return current_id, current_path
            
        except Exception as e:
            return None, f"Error resolving path from parent: {e}"
    
    def _find_file_in_directory(self, folder_id, filename):
        """在指定目录中查找文件"""
        try:
            result = self.drive_service.list_files(folder_id=folder_id, max_results=100)
            if not result['success']:
                # 如果是API错误，向上传递错误信息
                return {"_api_error": True, "error": result.get('error', 'API access failed')}
            
            for file in result['files']:
                if file['name'] == filename:
                    return file
            
            return None
        except Exception as e:
            return None
    
    def cmd_ls(self, path=None, detailed=False, recursive=False, show_hidden=False):
        """列出目录内容，支持递归、详细模式和扩展信息模式，支持文件路径"""
        if not self.drive_service:
            return {"success": False, "error": "Google Drive API服务未初始化"}
            
        current_shell = self.main_instance.get_current_shell()
        if not current_shell:
            return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
        
        # 首先将可能的远端绝对路径转换为逻辑路径
        if path:
            path = self.convert_absolute_to_logical(path)
        
        if path is None or path == ".":
            # 当前目录
            target_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
            display_path = current_shell.get("current_path", "~")
            used_config_id = None
            used_config_path = None
        elif path == "~":
            # 根目录 - 使用智能路径解析
            nearest_id, nearest_path = self.find_nearest_parent_id("~")
            if nearest_id and nearest_path == "~":  # 只有完全匹配才使用
                target_folder_id = nearest_id
                used_config_id = nearest_id
                used_config_path = nearest_path
            else:
                target_folder_id = self.main_instance.REMOTE_ROOT_FOLDER_ID
                used_config_id = None
                used_config_path = None
            display_path = "~"
        else:
            # 使用智能路径解析
            nearest_id, nearest_path = self.find_nearest_parent_id(path)
            if nearest_id and nearest_path:
                # 检查是否是精确匹配还是父目录匹配
                if nearest_path == path:
                    # 精确匹配，直接使用
                    target_folder_id = nearest_id
                    used_config_id = nearest_id
                    used_config_path = nearest_path
                else:
                    # 父目录匹配，需要从父目录开始解析子路径
                    resolve_result = self._resolve_from_parent_id(path, nearest_id, nearest_path)
                    if resolve_result[0]:  # 成功解析
                        target_folder_id = resolve_result[0]
                        used_config_id = nearest_id
                        used_config_path = nearest_path
                        
                        # 检查是否解析到的是文件的父目录（而不是目录本身）
                        if resolve_result[1] != path: 
                            filename = path.split('/')[-1]
                            file_result = self._find_file_in_directory(target_folder_id, filename)
                            
                            # 检查是否是API错误 - 使用bash格式错误
                            if isinstance(file_result, dict) and file_result.get("_api_error"):
                                # Bash-aligned error message - strict alignment
                                bash_error = f"ls: {path}: No such file or directory"
                                
                                # Detailed error information (for debugging)
                                result_processor = ResultProcessor(self.shell)
                                api_error = file_result.get("error", "API access failed")
                                base_error = f"Unable to find the id for subfolder '{path.split('/')[-2]}' from the current folder '{nearest_path}' (id: {target_folder_id})"
                                if api_error != "API access failed":
                                    base_error += f". \n\nAPI error: {api_error}"
                                detailed_error = result_processor._format_timeout_error_with_solutions(base_error, path, target_folder_id)
                                
                                # Debug print the detailed error (commented for production)
                                return {
                                    "success": False, 
                                    "error": bash_error,  # Bash-like error for main output
                                    "message": detailed_error,  # Detailed error for debugging
                                    "failed_path": path, 
                                    "failed_id": target_folder_id
                                }
                            elif file_result:
                                return {
                                    "success": True,
                                    "path": path,
                                    "files": [file_result],
                                    "folders": [],
                                    "count": 1,
                                    "mode": "single_file"
                                }
                            else:
                                return {"success": False, "error": f"ls: {path}: No such file or directory", "failed_path": path}
                    else:
                        # 从父目录解析失败，返回详细错误信息
                        error_msg = resolve_result[1] if resolve_result[1] else "Failed to resolve path from parent"
                        return {"success": False, "error": error_msg, "failed_path": path, "stuck_at_parent": nearest_path, "parent_id": nearest_id}
            else:
                # 回退到传统的路径解析
                target_folder_id, display_path = self.main_instance.resolve_drive_id(path, current_shell)
                used_config_id = None
                used_config_path = None
            
            display_path = path  # 保持逻辑路径格式
            
            if not target_folder_id:
                file_result = self.resolve_file_path(path, current_shell)
                if file_result:
                    return {
                        "success": True,
                        "path": path,
                        "files": [file_result],
                        "folders": [],
                        "count": 1,
                        "mode": "single_file"
                    }
                else:
                    return {"success": False, "error": f"ls: {path}: No such file or directory", "failed_path": path}
        
        if recursive:
            return self.ls_recursive(target_folder_id, display_path, detailed, show_hidden)
        else:
            # 内联_ls_single的逻辑
            result = self.drive_service.list_files(folder_id=target_folder_id, max_results=None)
            
            if result['success']:
                files = result['files']
                
                # 如果不显示隐藏文件，过滤掉以.开头的文件
                if not show_hidden:
                    files = [f for f in files if not f['name'].startswith('.')]
                
                # 添加网页链接到每个文件
                for file in files:
                    file['url'] = self.generate_web_url(file)
                
                # 按名称排序，文件夹优先
                folders = sorted([f for f in files if f['mimeType'] == 'application/vnd.google-apps.folder'], 
                                key=lambda x: x['name'].lower())
                other_files = sorted([f for f in files if f['mimeType'] != 'application/vnd.google-apps.folder'], 
                                    key=lambda x: x['name'].lower())
                
                # 去重处理
                seen_names = set()
                clean_folders = []
                clean_files = []
                
                # 处理文件夹
                for folder in folders:
                    if folder["name"] not in seen_names:
                        clean_folders.append(folder)
                        seen_names.add(folder["name"])
                
                # 处理文件
                for file in other_files:
                    if file["name"] not in seen_names:
                        clean_files.append(file)
                        seen_names.add(file["name"])
                
                if detailed:
                    # 详细模式：返回完整JSON
                    return {
                        "success": True,
                        "path": display_path,
                        "folder_id": target_folder_id,
                        "folder_url": self.generate_folder_url(target_folder_id),
                        "files": clean_files,  # 只有非文件夹文件
                        "folders": clean_folders,  # 只有文件夹
                        "count": len(clean_folders) + len(clean_files),
                        "mode": "detailed"
                    }
                else:
                    # bash风格：只返回文件名列表
                    return {
                        "success": True,
                        "path": display_path,
                        "folder_id": target_folder_id,
                        "files": clean_files,  # 只有非文件夹文件
                        "folders": clean_folders,  # 只有文件夹
                        "count": len(clean_folders) + len(clean_files),
                        "mode": "bash"
                    }
            else:
                # Bash-aligned error message (primary output) - strict alignment
                bash_error = f"ls: {display_path}: No such file or directory"
                
                # Detailed error information (for debugging)
                result_processor = ResultProcessor(self.shell)
                base_error = f"Unable to access '{display_path}'"
                if used_config_id:
                    base_error += f" (ID: {used_config_id})"
                detailed_error = result_processor._format_timeout_error_with_solutions(base_error, display_path, used_config_id)
                
                # Debug print the detailed error (commented for production)
                return {
                    "success": False, 
                    "error": bash_error,  # Bash-like error for main output
                    "message": detailed_error,  # Detailed error for debugging
                    "failed_path": display_path, 
                    "failed_id": used_config_id or target_folder_id, 
                    "config_source": used_config_path
                }

    def cmd_ls_by_id(self, folder_id, detailed=False, recursive=False, show_hidden=False):
        """根据文件夹ID直接列出目录内容"""
        if not self.drive_service:
            return {"success": False, "error": "Google Drive API service not initialized"}
        
        if not folder_id:
            return {"success": False, "error": "Folder ID cannot be empty"}
        
        # 验证文件夹ID格式（Google Drive ID通常是28个字符的字母数字组合）
        if not isinstance(folder_id, str) or len(folder_id) < 20:
            return {"success": False, "error": f"Invalid folder ID format: {folder_id}"}
        
        try:
            # 首先验证文件夹是否存在且可访问
            folder_info = self.drive_service.service.files().get(
                fileId=folder_id,
                fields='id,name,mimeType,trashed'
            ).execute()
            
            # 检查是否是文件夹
            if folder_info.get('mimeType') != 'application/vnd.google-apps.folder':
                return {
                    "success": False, 
                    "error": f"ID {folder_id} is not a folder, but a file: {folder_info.get('name', 'Unknown')}"
                }
            
            # 检查是否在回收站
            if folder_info.get('trashed', False):
                return {
                    "success": False, 
                    "error": f"Folder '{folder_info.get('name', 'Unknown')}' (ID: {folder_id}) is in the trash"
                }
            
            folder_name = folder_info.get('name', 'Unknown')
            
            if recursive:
                return self.ls_recursive(folder_id, f"[ID:{folder_id}]/{folder_name}", detailed, show_hidden)
            else:
                # 直接列出文件夹内容
                result = self.drive_service.list_files(folder_id=folder_id, max_results=None)
                if not result['success']:
                    return {
                        "success": False, 
                        "error": f"Failed to list folder content (ID: {folder_id}): {result.get('error', 'Unknown error')}"
                    }
                
                files = result['files']
                
                # 添加网页链接
                for file in files:
                    file['url'] = self.generate_web_url(file)
                
                # 过滤隐藏文件（如果需要）
                if not show_hidden:
                    files = [f for f in files if not f.get('name', '').startswith('.')]
                
                # 分离文件和文件夹
                clean_files = []
                clean_folders = []
                
                for file in files:
                    if file.get('mimeType') == 'application/vnd.google-apps.folder':
                        clean_folders.append(file)
                    else:
                        clean_files.append(file)
                
                return {
                    "success": True,
                    "path": f"[ID:{folder_id}]/{folder_name}",
                    "folder_id": folder_id,
                    "files": clean_files,
                    "folders": clean_folders,
                    "count": len(clean_folders) + len(clean_files),
                    "mode": "by_id"
                }
                
        except Exception as e:
            import traceback
            call_stack = ''.join(traceback.format_stack()[-3:])
            error_msg = str(e)
            
            # 处理常见的Google Drive API错误
            if "404" in error_msg or "not found" in error_msg.lower():
                return {
                    "success": False, 
                    "error": f"Folder ID does not exist or is not accessible: {folder_id}"
                }
            elif "403" in error_msg or "permission" in error_msg.lower():
                return {
                    "success": False, 
                    "error": f"No permission to access folder: {folder_id}"
                }
            else:
                return {
                    "success": False, 
                    "error": f"Error accessing folder (ID: {folder_id}): {error_msg}. Call stack: {call_stack}"
                }

    def ls_recursive(self, root_folder_id, root_path, detailed, show_hidden=False, max_depth=5):
        """递归列出目录内容"""
        try:
            all_items = []
            visited_folders = set()  # 防止循环引用
            
            def scan_folder(folder_id, folder_path, depth=0):
                # 深度限制
                if depth > max_depth:
                    return
                
                # 循环检测
                if folder_id in visited_folders:
                    return
                visited_folders.add(folder_id)
                
                result = self.drive_service.list_files(folder_id=folder_id, max_results=100)
                if not result['success']:
                    visited_folders.discard(folder_id)  # 失败时移除，允许重试
                    return
                
                files = result['files']
                
                # 添加网页链接
                for file in files:
                    file['url'] = self.generate_web_url(file)
                    file['path'] = folder_path
                    file['depth'] = depth
                    all_items.append(file)
                    
                    # 如果是文件夹，递归扫描
                    if file['mimeType'] == 'application/vnd.google-apps.folder':
                        sub_path = f"{folder_path}/{file['name']}" if folder_path != "~" else f"~/{file['name']}"
                        scan_folder(file['id'], sub_path, depth + 1)
                
                visited_folders.discard(folder_id)  # 扫描完成后移除，允许在其他路径中再次访问
            
            # 开始递归扫描
            scan_folder(root_folder_id, root_path)
            
            # 按路径和名称排序
            all_items.sort(key=lambda x: (x['path'], x['name'].lower()))
            
            # 分离文件夹和文件
            folders = [f for f in all_items if f['mimeType'] == 'application/vnd.google-apps.folder']
            other_files = [f for f in all_items if f['mimeType'] != 'application/vnd.google-apps.folder']
            
            if detailed:
                # 详细模式：返回嵌套的树形结构
                nested_structure = self.build_nested_structure(all_items, root_path)
                
                return {
                    "success": True,
                    "path": root_path,
                    "folder_id": root_folder_id,
                    "folder_url": self.generate_folder_url(root_folder_id),
                    "files": nested_structure["files"],
                    "folders": nested_structure["folders"],  # 每个文件夹包含自己的files和folders
                    "count": len(all_items),
                    "mode": "recursive_detailed"
                }
            else:
                # 简单模式：只返回基本信息
                return {
                    "success": True,
                    "path": root_path,
                    "folder_id": root_folder_id,
                    "files": other_files,
                    "folders": folders,
                    "all_items": all_items,
                    "count": len(all_items),
                    "mode": "recursive_bash"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error listing directory recursively: {e}"}

    def build_nested_structure(self, all_items, root_path):
        """构建嵌套的文件夹结构，每个文件夹包含自己的files和folders"""
        try:
            # 按路径分组所有项目
            path_groups = {}
            
            for item in all_items:
                path = item['path']
                if path not in path_groups:
                    path_groups[path] = {'files': [], 'folders': []}
                
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    path_groups[path]['folders'].append(item)
                else:
                    path_groups[path]['files'].append(item)
            
            # 构建嵌套结构
            def build_folder_content(folder_path):
                content = path_groups.get(folder_path, {'files': [], 'folders': []})
                
                # 为每个子文件夹递归构建内容
                enriched_folders = []
                for folder in content['folders']:
                    folder_copy = folder.copy()
                    sub_path = f"{folder_path}/{folder['name']}" if folder_path != "~" else f"~/{folder['name']}"
                    sub_content = build_folder_content(sub_path)
                    
                    # 将子内容添加到文件夹中
                    folder_copy['files'] = sub_content['files']
                    folder_copy['folders'] = sub_content['folders']
                    enriched_folders.append(folder_copy)
                
                return {
                    'files': content['files'],
                    'folders': enriched_folders
                }
            
            # 从根路径开始构建
            return build_folder_content(root_path)
            
        except Exception as e:
            return {'files': [], 'folders': [], 'error': str(e)}

    def generate_folder_url(self, folder_id):
        """生成文件夹的网页链接"""
        return f"https://drive.google.com/drive/folders/{folder_id}"
    
    def generate_web_url(self, file):
        """为文件生成网页链接"""
        file_id = file['id']
        mime_type = file['mimeType']
        
        if mime_type == 'application/vnd.google.colaboratory':
            # Colab文件
            return f"https://colab.research.google.com/drive/{file_id}"
        elif mime_type == 'application/vnd.google-apps.document':
            # Google文档
            return f"https://docs.google.com/document/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.spreadsheet':
            # Google表格
            return f"https://docs.google.com/spreadsheets/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.presentation':
            # Google幻灯片
            return f"https://docs.google.com/presentation/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.folder':
            # 文件夹
            return f"https://drive.google.com/drive/folders/{file_id}"
        else:
            # 其他文件（预览或下载）
            return f"https://drive.google.com/file/d/{file_id}/view"
    
    def resolve_file_path(self, file_path, current_shell):
        """解析文件路径，返回文件信息（如果存在）"""
        # 分离目录和文件名
        if "/" in file_path:
            dir_path = "/".join(file_path.split("/")[:-1])
            filename = file_path.split("/")[-1]
        else:
            dir_path = "."
            filename = file_path
        
        # 解析目录路径
        if dir_path == ".":
            parent_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
        else:
            parent_folder_id, _ = self.main_instance.resolve_drive_id(dir_path, current_shell)
            if not parent_folder_id:
                return None
        
        # 在父目录中查找文件
        result = self.drive_service.list_files(folder_id=parent_folder_id, max_results=100)
        
        if not result['success']:
            return None
        
        files = result.get('files', [])
        for i, file in enumerate(files):
            file_name = file.get('name', 'UNKNOWN')
            if file_name == filename:
                file['url'] = self.generate_web_url(file)
                return file
        
        return None

    
    def print_detailed_listing(self, items):
        """打印详细的列表信息，类似 ls -la 的表格格式
        
        Args:
            items: 文件和文件夹列表
        """
        from datetime import datetime
        
        # 计算列宽
        max_size_width = 0
        for item in items:
            size_str = self._format_size(item.get('size', ''))
            max_size_width = max(max_size_width, len(size_str))
        
        # 打印标题行
        print(f"{'TYPE':<8} {'SIZE':>{max_size_width}} {'MODIFIED':<20} {'ID':<40} {'NAME'}")
        print("-" * (8 + max_size_width + 20 + 40 + 50))
        
        # 打印每个项目
        for item in items:
            # 类型
            mime_type = item.get('mimeType', '')
            if mime_type == 'application/vnd.google-apps.folder':
                type_str = 'DIR'
            else:
                type_str = 'FILE'
            
            # 大小
            size_str = self._format_size(item.get('size', ''))
            
            # 修改时间
            modified_time = item.get('modifiedTime', '')
            if modified_time:
                try:
                    dt = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
                    time_str = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    time_str = modified_time[:16]  # 截取前16个字符
            else:
                time_str = '-'
            
            # ID
            file_id = item.get('id', '-')
            
            # 名称
            name = item.get('name', 'Unknown')
            if mime_type == 'application/vnd.google-apps.folder':
                name += '/'
            
            # 打印行
            print(f"{type_str:<8} {size_str:>{max_size_width}} {time_str:<20} {file_id:<40} {name}")
    
    def _format_size(self, size):
        """格式化文件大小
        
        Args:
            size: 文件大小（字节）
            
        Returns:
            格式化的大小字符串
        """
        if not size:
            return '-'
        
        try:
            size_bytes = int(size)
            
            # 转换为人类可读格式
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size_bytes < 1024.0:
                    if unit == 'B':
                        return f"{size_bytes:.0f}{unit}"
                    else:
                        return f"{size_bytes:.1f}{unit}"
                size_bytes /= 1024.0
            
            return f"{size_bytes:.1f}PB"
        except (ValueError, TypeError):
            return '-'
    
    def cmd_ls_remote(self, path=None, detailed=False, recursive=False, show_hidden=False):
        """使用远程bash命令强制刷新ls结果"""
        try:
            # 如果提供了path，需要将逻辑路径转换为远程绝对路径
            if path:
                # 首先将可能的远端绝对路径转换为逻辑路径
                path = self.convert_absolute_to_logical(path)
                
                # 获取当前shell信息
                current_shell = self.main_instance.get_current_shell()
                if not current_shell:
                    return {"success": False, "error": "没有活跃的远程shell"}
                
                # 路径已经在execute_shell_command中统一处理，直接使用
                remote_path = path
            else:
                # 如果没有提供path，使用当前工作目录的远程绝对路径
                current_shell = self.main_instance.get_current_shell()
                if current_shell:
                    remote_path = current_shell.get("remote_cwd", None)
                else:
                    remote_path = None
            
            # 构建bash ls命令
            ls_args = []
            if detailed:
                ls_args.append('-la')
            else:
                ls_args.append('-l')
            
            if show_hidden and not detailed:  # -la已经包含了-a
                ls_args.append('-a')
            
            if recursive:
                ls_args.append('-R')
            
            # 构建完整命令
            if remote_path:
                full_command = f"ls {' '.join(ls_args)} '{remote_path}'"
            else:
                full_command = f"ls {' '.join(ls_args)}"
            
            # 通过远程bash执行
            result = self.shell.execute_command_interface('bash', ['-c', full_command])
            
            if result.get('success'):
                data = result.get('data', {})
                exit_code = data.get('exit_code', 0)
                stdout = data.get('stdout', '')
                stderr = data.get('stderr', '')
                
                # 检查ls命令是否成功执行（exit_code为0）
                if exit_code == 0:
                    # 解析bash ls输出为GDS格式
                    return self._parse_bash_ls_output(stdout, path or "~")
                else:
                    # ls命令失败（文件不存在等）
                    return {"success": False, "error": stderr.strip()}
            else:
                import traceback
                data = result.get('data', {})
                error = result.get('error', data.get('stderr', f'Command failed. Call stack: {traceback.format_exc()}'))
                return {"success": False, "error": f"Force refresh failed: {error}"}
                
        except Exception as e:
            return {"success": False, "error": f"Force refresh error: {str(e)}"}
    
    def _parse_bash_ls_output(self, stdout, base_path):
        """解析bash ls输出为GDS格式"""
        try:
            lines = stdout.strip().split('\n')
            files = []
            folders = []
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('total'):
                    continue
                
                # 简单解析ls -l输出
                parts = line.split()
                if len(parts) < 9:
                    continue
                
                permissions = parts[0]
                name = ' '.join(parts[8:])  # 文件名可能包含空格
                
                # 跳过. 和 ..
                if name in ['.', '..']:
                    continue
                
                item = {
                    'name': name,
                    'id': f"bash_{name}",  # 临时ID
                    'mimeType': 'application/vnd.google-apps.folder' if permissions.startswith('d') else 'text/plain',
                    'size': parts[4] if not permissions.startswith('d') else None,
                    'modifiedTime': f"{parts[5]} {parts[6]} {parts[7]}",
                    'url': f"file://{base_path}/{name}"
                }
                
                if permissions.startswith('d'):
                    folders.append(item)
                else:
                    files.append(item)
            
            return {
                "success": True,
                "files": files,
                "folders": folders,
                "display_path": base_path,
                "force_refreshed": True
            }
            
        except Exception as e:
            return {"success": False, "error": f"Parse bash ls output error: {str(e)}"}

    def show_help(self):
        """显示ls命令的帮助信息"""
        help_text = """ls - list directory contents

Usage:
  ls [path] [options]
  ls --id <folder_id> [options]

Arguments:
  path                     Directory path to list (default: current directory)

Options:
  --detailed               Show detailed file information (type, size, modified time, ID, name)
  --id <folder_id>         List directory by Google Drive folder ID (cannot be used with path)
  -R                       Recursive listing
  -a, --all                Show hidden files (files starting with .)
  -f, --force              Force mode (use remote bash to bypass API cache)
  -d                       Directory mode
  -h, --help               Show this help message

Examples:
  ls                       List current directory
  ls /path/to/dir          List specific directory
  ls --detailed            Show detailed information with file IDs
  ls --id 1GgaX0K7_QtZblGmj0fAK6E8CFZbC0P0B    List directory by ID
  ls --id 1GgaX0K7_QtZblGmj0fAK6E8CFZbC0P0B --detailed    List by ID with details
  ls -R                    List recursively
  ls ~/Documents           List Documents folder

Note: Use 'ls --detailed' to get folder IDs for use with --id option.
"""
        print(help_text)

