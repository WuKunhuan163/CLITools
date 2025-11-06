#!/usr/bin/env python3
"""
Google Drive Shell - Path Resolver Module

This module provides comprehensive path resolution and management functionality for the Google Drive Shell system.
It handles the complex mapping between local paths, remote logical paths, and Google Drive folder IDs.

Key Features:
- Logical path resolution (~/path, @/path formats)
- Remote absolute path calculation
- Google Drive folder ID resolution
- Path normalization and validation
- Support for both user space (~) and environment space (@) paths
- Integration with Google Drive API for folder ID lookup

Path Formats:
- Logical paths: ~/documents/file.txt (user space), @/python/script.py (environment space)
- Remote absolute paths: /content/drive/MyDrive/documents/file.txt
- Google Drive IDs: Folder and file IDs for API operations

Classes:
    PathResolver: Main path resolution class handling all path operations

Dependencies:
    - Google Drive API service for folder ID resolution
    - Path constants for base directory definitions
    - Shell state management for current directory tracking
"""

import os
import sys
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

class PathResolver:
    """Google Drive Shell Path Resolver"""

    def __init__(self, drive_service=None, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance

    def expand_path(self, path):
        """展开路径，处理~等特殊字符"""
        try:
            import os
            return os.path.expanduser(os.path.expandvars(path))
        except Exception as e:
            print(f"Path expansion failed: {e}")
            return path

    def resolve_drive_id(self, path, current_shell=None):
        """
        解析路径，返回对应的Google Drive文件夹ID和逻辑路径
        重构后的版本：使用resolve_remote_absolute_path获取逻辑路径，然后从逻辑路径获取Drive ID
        """
        if not self.drive_service:
            return None, None
            
        if not current_shell:
            current_shell = self.main_instance.get_current_shell()
            
        if not current_shell:
            return None, None
        
        try:
            # 步骤1：使用resolve_remote_absolute_path获取规范化的逻辑路径（~/xxx格式）
            logical_path = self.resolve_remote_absolute_path(path, current_shell, return_logical=True)
            
            # 步骤2：从逻辑路径获取Drive ID
            # 处理特殊路径：DRIVE_EQUIVALENT
            def _resolve_id_by_parts(path_parts, base_folder_id, base_logical_path):
                """
                从路径parts逐级获取Drive ID（简化版本）
                
                Args:
                    path_parts (list): 路径组件列表，如["tmp", "subfolder"]
                    base_folder_id (str): 基础文件夹ID
                    base_logical_path (str): 基础逻辑路径（如"~"或"@drive_equivalent"）
                    
                Returns:
                    tuple: (folder_id, logical_path) or (None, None) if path doesn't exist
                """
                current_id = base_folder_id
                current_logical_path = base_logical_path
                
                try:
                    for part in path_parts:
                        # 跳过空组件
                        if not part:
                            continue
                        
                        # 查找该部分对应的文件夹
                        files_result = self.drive_service.list_files(folder_id=current_id, max_results=100)
                        if not files_result['success']:
                            return None, None
                        
                        found_folder = None
                        for file in files_result['files']:
                            if file['name'] == part and file['mimeType'] == 'application/vnd.google-apps.folder':
                                found_folder = file
                                break
                        
                        if not found_folder:
                            # 路径不存在
                            return None, None
                        
                        # 更新当前ID和逻辑路径
                        current_id = found_folder['id']
                        if current_logical_path == "~":
                            current_logical_path = f"~/{part}"
                        elif current_logical_path == "@":
                            current_logical_path = f"@/{part}"
                        elif current_logical_path == "@drive_equivalent":
                            current_logical_path = f"@drive_equivalent/{part}"
                        else:
                            current_logical_path = f"{current_logical_path}/{part}"
                    
                    return current_id, current_logical_path
                    
                except Exception as e:
                    print(f"Error: Resolve ID by parts failed: {e}")
                    return None, None

            # 处理@路径（代表REMOTE_ENV）
            if logical_path == "@":
                return self.main_instance.REMOTE_ENV_FOLDER_ID, "@"
            elif logical_path.startswith("@/"):
                relative_parts = logical_path[2:].split("/")
                return _resolve_id_by_parts(
                    relative_parts, 
                    self.main_instance.REMOTE_ENV_FOLDER_ID, 
                    "@"
                )
            
            # 处理@drive_equivalent路径（向后兼容）
            if logical_path == "@drive_equivalent":
                return self.main_instance.DRIVE_EQUIVALENT_FOLDER_ID, "@drive_equivalent"
            elif logical_path.startswith("@drive_equivalent/"):
                relative_parts = logical_path[len("@drive_equivalent/"):].split("/")
                return _resolve_id_by_parts(
                    relative_parts, 
                    self.main_instance.DRIVE_EQUIVALENT_FOLDER_ID, 
                    "@drive_equivalent"
                )
            # 处理REMOTE_ROOT路径（~/xxx格式）
            elif logical_path == "~":
                return self.main_instance.REMOTE_ROOT_FOLDER_ID, "~"
            elif logical_path.startswith("~/"):
                # 从REMOTE_ROOT开始逐层访问
                relative_parts = logical_path[2:].split("/") if logical_path[2:] else []
                return _resolve_id_by_parts(
                    relative_parts, 
                    self.main_instance.REMOTE_ROOT_FOLDER_ID, 
                    "~"
                )
            else:
                # 不应该到达这里（所有路径都应该被规范化为~/xxx格式）
                print(f"Warning: Unexpected logical_path format: {logical_path}")
                return None, None
                
        except Exception as e:
            print(f"Error: Resolve drive ID failed: {e}")
            return None, None
    
    def undo_local_path_user_expansion(self, command_or_path):
        """
        将bash shell扩展的本地路径转换回远程路径格式
        
        当用户输入 'GDS cd ~/tmp/test' 时，bash会将 ~/tmp/test 扩展为 /Users/username/tmp/test
        这个函数将其转换回 ~/tmp/test 格式，以便正确解析为远程路径
        
        Args:
            command_or_path: 可以是完整的命令字符串或单个路径
        
        Returns:
            转换后的命令字符串或路径
        """
        import os
        import uuid
        import subprocess
        
        # 获取用户的home目录
        home_dir = os.path.expanduser("~")
        
        # 用户建议的完整方案：
        # 步骤1: 用hash保护原始的~，避免被误替换
        tilde_placeholder = f"TILDE_PLACEHOLDER_{uuid.uuid4().hex[:8].upper()}"
        protected_command = command_or_path.replace('~', tilde_placeholder)
        
        # 步骤2: 将已展开的home目录路径替换回~
        # 这些~是"可疑的"，可能是被错误展开的路径
        suspicious_command = protected_command.replace(home_dir, '~')
        
        # 步骤3: 用bash -c -x测试，分块处理重定向
        # 如果这些~被bash展开了，说明它们确实是被错误展开的路径
        try:
            # 检测重定向并分块处理
            redirect_operators = ['>', '>>', '<', '2>', '2>>', '&>', '&>>', '2>&1', '|']
            main_command = suspicious_command
            redirect_part = ""
            
            # 找到重定向操作符，分离主命令和重定向部分
            for op in redirect_operators:
                if op in suspicious_command:
                    op_index = suspicious_command.find(op)
                    main_command = suspicious_command[:op_index].strip()
                    redirect_part = suspicious_command[op_index:].strip()
                    break
            
            
            # 对主命令用bash -c -x测试
            if main_command:
                result = subprocess.run(
                    ['bash', '-c', '-x', main_command],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    cwd=os.path.expanduser('~/tmp')
                )
                
                if result.stderr:
                    lines = result.stderr.strip().split('\n')
                    for line in lines:
                        if line.startswith('+ '):
                            expanded_main = line[2:]  # 去掉"+ "前缀
                            
                            # 将展开的home_dir替换回~，将placeholder恢复为~
                            final_main = expanded_main.replace(home_dir, '~')
                            final_main = final_main.replace(tilde_placeholder, '~')
                            
                            # 处理重定向部分的路径
                            if redirect_part:
                                final_redirect = redirect_part.replace(home_dir, '~')
                                final_redirect = final_redirect.replace(tilde_placeholder, '~')
                                final_command = final_main + ' ' + final_redirect
                            else:
                                final_command = final_main
                            
                            return final_command
                            
        except Exception as e:
            pass
        
        # 回退方案：简单替换
        result = suspicious_command.replace(tilde_placeholder, '~')
        return result
    
    def get_parent_path(self, path):
        """获取路径的父目录，支持~和@前缀"""
        if path == "~":
            return "~"  # 根目录没有父目录，返回自己
        
        if path == "@":
            return "@"  # REMOTE_ENV根目录没有父目录，返回自己
        
        if path.startswith("~/"):
            parts = path.split("/")
            if len(parts) <= 2:  # ~/something -> ~
                return "~"
            else:  # ~/a/b/c -> ~/a/b
                return "/".join(parts[:-1])
        
        if path.startswith("@/"):
            parts = path.split("/")
            if len(parts) <= 2:  # @/something -> @
                return "@"
            else:  # @/a/b/c -> @/a/b
                return "/".join(parts[:-1])
        
        return path
    
    def join_paths(self, base_path, relative_path):
        """连接基础路径和相对路径，支持~和@前缀"""
        if not relative_path:
            return base_path
        
        if base_path == "~":
            return f"~/{relative_path}"
        elif base_path == "@":
            return f"@/{relative_path}"
        else:
            return f"{base_path}/{relative_path}"
    
    def normalize_path_components(self, base_path, relative_path):
        """规范化路径组件，处理路径中的 .. 和 .
        
        支持~（REMOTE_ROOT）和@（REMOTE_ENV）前缀
        """
        try:
            # 先连接路径
            combined_path = self.join_paths(base_path, relative_path)
            
            # 处理@路径（REMOTE_ENV）
            if combined_path == "@":
                return "@"
            
            if combined_path.startswith("@/"):
                # 移除 @/ 前缀
                path_without_root = combined_path[2:]
                if not path_without_root:
                    return "@"
                
                # 分割路径组件
                components = path_without_root.split("/")
                normalized_components = []
                
                for component in components:
                    if component == "." or component == "":
                        # 跳过当前目录和空组件
                        continue
                    elif component == "..":
                        # 父目录 - 移除上一个组件
                        if normalized_components:
                            normalized_components.pop()
                        # 如果没有组件可移除，说明已经到根目录，忽略
                    else:
                        # 普通目录名
                        normalized_components.append(component)
                
                # 重建路径
                if not normalized_components:
                    return "@"
                else:
                    return "@/" + "/".join(normalized_components)
            
            # 处理~路径（REMOTE_ROOT）
            if combined_path == "~":
                return "~"
            
            if not combined_path.startswith("~/"):
                return combined_path
            
            # 移除 ~/ 前缀
            path_without_root = combined_path[2:]
            if not path_without_root:
                return "~"
            
            # 分割路径组件
            components = path_without_root.split("/")
            normalized_components = []
            
            for component in components:
                if component == "." or component == "":
                    # 跳过当前目录和空组件
                    continue
                elif component == "..":
                    # 父目录 - 移除上一个组件
                    if normalized_components:
                        normalized_components.pop()
                    # 如果没有组件可移除，说明已经到根目录，忽略
                else:
                    # 普通目录名
                    normalized_components.append(component)
            
            # 重建路径
            if not normalized_components:
                result = "~"
            else:
                result = "~/" + "/".join(normalized_components)
            
            
            return result
                
        except Exception as e:
            # 如果规范化失败，返回原始连接的路径
            return self.join_paths(base_path, relative_path)

    def resolve_remote_absolute_path(self, path, current_shell=None, return_logical=False):
        """
        通用路径解析接口：将相对路径解析为远端绝对路径
        
        Args:
            path (str): 要解析的路径
            current_shell (dict): 当前shell状态，如果为None则自动获取
            return_logical (bool): 如果为True，返回逻辑路径（~/xxx），否则返回完整远端路径
            
        Returns:
            str: 解析后的路径（根据return_logical参数决定格式）
        """
        try:
            if not current_shell:
                current_shell = self.main_instance.get_current_shell()
                if not current_shell:
                    raise ValueError("Current shell or default shell both not available for path resolution. ")
            
            # 获取当前路径
            current_path = current_shell.get("current_path", "~")
            remote_root_path = self.main_instance.REMOTE_ROOT
            remote_env_path = self.main_instance.REMOTE_ENV
            
            #### Special Processing for REMOTE_ROOT and REMOTE_ENV ####
            #### 正常来讲，用户不会输入绝对路径，而是输入~以及@开头的逻辑路径 ####
            # 首先检查是否是完整的远程路径，需要转换回逻辑路径
            if path.startswith(remote_root_path):
                if path == remote_root_path:
                    logical_path = "~"
                elif path.startswith(f"{remote_root_path}/"):
                    relative_part = path[len(remote_root_path) + 1:]
                    logical_path = f"~/{relative_part}"
                else:
                    logical_path = path  # 不应该到这里，但保持原样
                
                if return_logical:
                    return logical_path
                else:
                    return path  # 已经是绝对路径
            elif path.startswith(remote_env_path):
                if path == remote_env_path:
                    logical_path = "@"
                elif path.startswith(f"{remote_env_path}/"):
                    relative_part = path[len(remote_env_path) + 1:]
                    logical_path = f"@/{relative_part}"
                else:
                    logical_path = path  # 不应该到这里，但保持原样
                
                if return_logical:
                    return logical_path
                else:
                    return path  # 已经是绝对路径
            
            # 如果仍然是绝对路径（以/开头），转换为~/xxx格式
            elif path.startswith("/"):
                # 真正的绝对路径，映射为逻辑路径
                # 例如 /tmp/file.txt -> ~/tmp/file.txt
                relative_part = path[1:]  # 去掉前导的 /
                if relative_part:
                    logical_path = f"~/{relative_part}"
                else:
                    logical_path = "~"
                # 根据return_logical决定返回格式
                if return_logical:
                    return logical_path
                else:
                    return f"{remote_root_path}/{relative_part}" if relative_part else remote_root_path
            
            # 处理@开头的路径（代表REMOTE_ENV）
            if path.startswith("@"):
                logical_path = path
                if '../' in path or '/./' in path or path.endswith('/..') or path.endswith('/.'):
                    logical_path = self.normalize_path_components("@", path[2:] if path.startswith("@/") else path[1:])
                
                # 根据return_logical决定返回格式
                if return_logical:
                    return logical_path
                else:
                    if logical_path == "@":
                        return remote_env_path
                    elif logical_path.startswith("@/"):
                        relative_part = logical_path[2:]
                        return f"{remote_env_path}/{relative_part}"
                    else:
                        return f"{remote_env_path}/{logical_path[1:]}"
            
            # 计算逻辑路径（~/xxx格式）
            if path.startswith("~"):
                logical_path = path
                if '../' in path or '/./' in path or path.endswith('/..') or path.endswith('/.'):
                    logical_path = self.normalize_path_components("~", path[2:] if path.startswith("~/") else path[1:])
            elif path == "." or path == "":
                # 当前目录
                logical_path = current_path
            else:
                # 相对路径，需要基于当前目录计算
                if path.startswith("./"):
                    path = path[2:]  # 移除./
                
                # 处理父目录路径
                if path == "..":
                    logical_path = self.get_parent_path(current_path)
                elif path.startswith("../"):
                    # 递归处理父目录路径
                    parent_path = self.get_parent_path(current_path)
                    remaining_path = path[3:]  # 移除../
                    # 递归调用，传入parent_path作为current_path，同时传递return_logical参数
                    return self.resolve_remote_absolute_path(remaining_path, {"current_path": parent_path}, return_logical=return_logical)
                else:
                    # 普通相对路径，使用normalize处理
                    logical_path = self.normalize_path_components(current_path, path)
            
            # 根据return_logical参数决定返回格式
            if return_logical:
                return logical_path
            else:
                if logical_path == "~":
                    return remote_root_path
                elif logical_path.startswith("~/"):
                    relative_part = logical_path[2:]
                    return f"{remote_root_path}/{relative_part}"
                else:
                    # 不应该到达这里，但作为fallback
                    return f"{remote_root_path}/{logical_path}"
            
        except Exception as e:
            # 如果解析失败，返回原路径
            return path
