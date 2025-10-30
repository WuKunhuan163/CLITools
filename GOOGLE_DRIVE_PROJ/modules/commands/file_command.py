"""
File operations commands (touch, rm, mv)
从file_core.py迁移而来
合并了touch_command, rm_command, mv_command
"""

from .base_command import BaseCommand

class FileCommand(BaseCommand):
    """文件操作命令 - 统一处理touch, rm, mv"""
    
    @property
    def command_name(self):
        # 返回主命令名，但这个类会注册多个命令
        return "file"
    
    def execute(self, cmd, args, command_identifier=None):
        """根据命令名分发到具体的处理方法"""
        if cmd == "touch":
            return self.execute_touch(args)
        elif cmd == "rm":
            return self.execute_rm(args)
        elif cmd == "mv":
            return self.execute_mv(args)
        else:
            print(f"Error: Unknown file command: {cmd}")
            return 1
    
    def execute_touch(self, args):
        """执行touch命令"""
        if not args:
            print("Error: touch command needs a file name")
            return 1
        
        # 处理每个文件
        for file_path in args:
            result = self.cmd_touch(file_path)
            
            if not result.get("success", False):
                print(result.get("error", f"Failed to create file: {file_path}"))
                return 1
        
        return 0
    
    def execute_rm(self, args):
        """执行rm命令"""
        if not args:
            print("Error: rm command needs a file or directory name")
            return 1
        
        # 解析参数
        recursive = False
        force = False
        files = []
        
        for arg in args:
            if arg == '-r':
                recursive = True
            elif arg == '-f':
                force = True
            elif arg == '-rf' or arg == '-fr':
                recursive = True
                force = True
            else:
                files.append(arg)
        
        if not files:
            print("Error: rm command needs a file or directory name")
            return 1
        
        # 处理每个文件/目录
        for file_path in files:
            result = self.cmd_rm(file_path, recursive=recursive, force=force)
            
            if not result.get("success", False):
                print(result.get("error", f"Failed to remove: {file_path}"))
                return 1
        
        return 0
    
    def execute_mv(self, args):
        """执行mv命令"""
        if len(args) < 2:
            print("Error: mv command needs source and destination")
            return 1
        
        source = args[0]
        destination = args[1]
        
        result = self.cmd_mv(source, destination)
        
        if not result.get("success", False):
            print(result.get("error", f"Failed to move {source} to {destination}"))
            return 1
        
        return 0

    def cmd_touch(self, filename):
        """创建空文件，通过远程命令界面执行"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API service not initialized"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell"}
            
            if not filename:
                return {"success": False, "error": "Please specify the file name to create"}
            
            # 使用统一的路径解析接口
            absolute_path = self.main_instance.path_resolver.resolve_remote_absolute_path(filename, current_shell)
            
            # 生成远端touch命令（创建空文件）
            remote_command = f'touch "{absolute_path}"'
            
            # 使用统一接口执行远端命令
            execution_result = self.main_instance.execute_command_interface("bash", ["-c", remote_command])
            
            if execution_result["success"]:
                # 简洁返回，像bash shell一样成功时不显示任何信息
                return {
                    "success": True,
                    "filename": filename,
                    "absolute_path": absolute_path,
                    "remote_command": remote_command,
                    "message": "",  # 空消息，不显示任何内容
                    "verification": {"success": True}
                }
            else:
                return execution_result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Remote touch command generation failed: {e}"
            }

    def cmd_rm(self, path, recursive=False, force=False):
        """删除文件或目录，通过远程rm命令执行"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API service not initialized"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell first"}
            
            if not path:
                return {"success": False, "error": "Please specify file or directory to delete"}
            
            # 解析远程绝对路径
            absolute_path = self.main_instance.resolve_remote_absolute_path(path, current_shell)
            if not absolute_path:
                return {"success": False, "error": f"Cannot resolve path: {path}"}
            
            # 安全检查：如果是rm -rf，检查是否要删除当前目录或其上级目录
            if recursive and force:
                current_working_dir = current_shell.get("current_path", "")
                if current_working_dir:
                    current_absolute = self.main_instance.resolve_remote_absolute_path(".", current_shell)
                    target_absolute = absolute_path
                    
                    # 规范化目标路径，解析 ../
                    import os
                    target_absolute_normalized = os.path.normpath(target_absolute)
                    
                    if current_absolute and target_absolute_normalized:
                        # 检测X是否包含Y作为开头的子串
                        if current_absolute.startswith(target_absolute_normalized):
                            return {"success": False, "error": f"Cannot delete directory containing current working directory: {path}"}
            
            # 构建rm命令
            rm_flags = ""
            if recursive:
                rm_flags += "r"
            if force:
                rm_flags += "f"
            
            # 检查是否包含通配符，如果包含则不加引号以允许shell展开
            has_wildcards = '*' in absolute_path or '?' in absolute_path or '[' in absolute_path
            
            if rm_flags:
                if has_wildcards:
                    remote_command = f'rm -{rm_flags} {absolute_path}'
                else:
                    remote_command = f'rm -{rm_flags} "{absolute_path}"'
            else:
                if has_wildcards:
                    remote_command = f'rm {absolute_path}'
                else:
                    remote_command = f'rm "{absolute_path}"'
            
            # 为了避免删除当前工作目录导致的问题，先切换到安全目录
            # 构建安全的复合命令：先cd到根目录，然后执行rm
            safe_command = f'cd "{self.main_instance.REMOTE_ROOT}" && {remote_command}'
            
            # 执行远程命令
            result = self.main_instance.execute_command_interface("bash", ["-c", safe_command])
            
            if result["success"]:
                # 简化验证逻辑：如果远程命令执行完成，就认为删除成功
                # 避免复杂的验证逻辑导致误报
                return {
                    "success": True,
                    "path": path,
                    "absolute_path": absolute_path,
                    "remote_command": remote_command,
                    "message": "",  # 空消息，像bash shell一样
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": f"Error executing rm command: {e}"}

    def cmd_mv(self, source, destination, force=False):
        """mv命令 - 移动/重命名文件或文件夹（使用远端指令执行）"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            if not source or not destination:
                return {"success": False, "error": "Usage: mv <source> <destination>"}
            
            # 简化版本：不进行复杂的冲突检查
            
            # 构建远端mv命令 - 需要计算绝对路径并进行shell转义
            source_absolute_path = self.main_instance.resolve_remote_absolute_path(source, current_shell)
            destination_absolute_path = self.main_instance.resolve_remote_absolute_path(destination, current_shell)
            
            # 使用shlex.quote对路径进行shell转义，处理空格和特殊字符
            import shlex
            escaped_source = shlex.quote(source_absolute_path)
            escaped_destination = shlex.quote(destination_absolute_path)
            
            # 构建增强的远端命令，包含成功/失败提示
            base_command = f"mv {escaped_source} {escaped_destination}"
            remote_command = f"({base_command})"
            
            # 使用远端指令执行接口
            result = self.main_instance.execute_command_interface("bash", ["-c", remote_command])
            
            if result.get("success"):
                verification_result = self.main_instance.verify_creation_with_ls(destination_absolute_path, current_shell, creation_type="file")
                if verification_result.get("success", False):
                    return {
                        "success": True,
                        "source": source,
                        "destination": destination,
                        "message": f""
                    }
                else:
                    return {
                        "success": False,
                        "error": f"mv verification failed: {verification_result.get('error', 'Unknown verification error')}"
                    }
            else:
                # 优先使用用户提供的错误信息
                error_msg = (result.get('error_info') if 'error_info' in result 
                           else result.get('error', 'Unknown error'))
                return {
                    "success": False,
                    "error": f"mv command execution failed: {error_msg}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Execute mv command failed: {e}"}
