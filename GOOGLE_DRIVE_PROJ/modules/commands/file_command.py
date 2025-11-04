"""
File operations commands
"""

from .base_command import BaseCommand

class FileCommand(BaseCommand):
    """文件操作命令 - 统一处理touch, rm, mv"""
    
    @property
    def command_name(self):
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
        # 检查是否请求帮助
        if args and (args[0] == '--help' or args[0] == '-h'):
            self.show_touch_help()
            return 0
        
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
        # 检查是否请求帮助
        if args and (args[0] == '--help' or args[0] == '-h'):
            self.show_rm_help()
            return 0
        
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
        # 检查是否请求帮助
        if args and (args[0] == '--help' or args[0] == '-h'):
            self.show_mv_help()
            return 0
        
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
            
            # 路径已经在execute_shell_command中统一处理，直接使用
            absolute_path = filename
            
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
        if not self.drive_service:
            return {"success": False, "error": "Google Drive API service not initialized"}
            
        current_shell = self.main_instance.get_current_shell()
        if not current_shell:
            return {"success": False, "error": "No active remote shell, please create or switch to a shell first"}
        
        if not path:
            return {"success": False, "error": "Please specify file or directory to delete"}
        
        # 路径已经在execute_shell_command中统一处理，直接使用
        absolute_path = path
        
        # 安全检查：如果是rm -rf，检查是否要删除当前目录或其上级目录
        if recursive and force:
            current_working_dir = current_shell.get("current_path", "")
            if current_working_dir:
                # 将当前目录的逻辑路径转换为绝对路径进行比较
                if current_working_dir.startswith("~/"):
                    current_absolute = f"{self.main_instance.REMOTE_ROOT}/{current_working_dir[2:]}"
                elif current_working_dir == "~":
                    current_absolute = self.main_instance.REMOTE_ROOT
                elif current_working_dir.startswith("@/"):
                    current_absolute = f"{self.main_instance.REMOTE_ENV}/{current_working_dir[2:]}"
                elif current_working_dir == "@":
                    current_absolute = self.main_instance.REMOTE_ENV
                else:
                    current_absolute = current_working_dir
                
                target_absolute = absolute_path
                
                # 处理相对路径（如 . 和 ..）
                import os
                if target_absolute == ".":
                    target_absolute = current_absolute
                elif target_absolute.startswith("./"):
                    target_absolute = os.path.join(current_absolute, target_absolute[2:])
                elif target_absolute.startswith("../"):
                    target_absolute = os.path.join(current_absolute, target_absolute)
                
                # 规范化路径，解析 ../
                current_absolute_normalized = os.path.normpath(current_absolute)
                target_absolute_normalized = os.path.normpath(target_absolute)
                
                if current_absolute_normalized and target_absolute_normalized:
                    # 检测当前目录是否在要删除的目录内（或就是要删除的目录）
                    if (current_absolute_normalized == target_absolute_normalized or 
                        current_absolute_normalized.startswith(target_absolute_normalized + "/")):
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
        
        # 直接执行rm命令，不改变工作目录
        safe_command = remote_command
        
        # 执行远程命令
        result = self.main_instance.execute_command_interface("bash", ["-c", safe_command])
        
        if result.get("success", False):
            return {
                "success": True,
                "path": path,
                "absolute_path": absolute_path,
                "remote_command": remote_command,
                "message": "", 
            }
        else:
            return result

    def cmd_mv(self, source, destination, force=False):
        """mv命令 - 移动/重命名文件或文件夹（使用远端指令执行）"""
        current_shell = self.main_instance.get_current_shell()
        if not current_shell:
            return {"success": False, "error": "No active remote shell"}
        
        if not source or not destination:
            return {"success": False, "error": "Usage: mv <source> <destination>"}
        
        # 路径已经在execute_shell_command中统一处理，直接使用
        source_absolute_path = source
        destination_absolute_path = destination
        
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
            verification_result = self.main_instance.verify_with_ls(destination_absolute_path, current_shell, creation_type="file")
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
    
    def show_touch_help(self):
        """显示touch命令的帮助信息"""
        help_text = """touch - create empty files

Usage:
  touch <file> [file2 ...] [options]

Arguments:
  file                     File path(s) to create

Options:
  -h, --help               Show this help message

Description:
  Create empty files if they don't exist.
  Supports creating multiple files at once.
  Similar to the Unix touch command.

Examples:
  touch newfile.txt        Create a new empty file
  touch file1 file2 file3  Create multiple files
  touch ~/docs/note.txt    Create file with absolute path
"""
        print(help_text)
    
    def show_rm_help(self):
        """显示rm命令的帮助信息"""
        help_text = """rm - remove files or directories

Usage:
  rm [options] <file/directory> ...

Arguments:
  file/directory           File or directory path(s) to remove

Options:
  -r                       Remove directories recursively
  -f                       Force removal without confirmation
  -rf, -fr                 Recursive and force removal
  -h, --help               Show this help message

Description:
  Remove files or directories from Google Drive.
  Use -r flag for directories and -f to skip confirmation.
  BE CAREFUL: This operation cannot be undone easily.

Examples:
  rm file.txt              Remove a file
  rm -r directory          Remove a directory recursively
  rm -rf temp              Force remove directory
  rm file1 file2 file3     Remove multiple files
"""
        print(help_text)
    
    def show_mv_help(self):
        """显示mv命令的帮助信息"""
        help_text = """mv - move or rename files and directories

Usage:
  mv <source> <destination> [options]

Arguments:
  source                   Source file or directory path
  destination              Destination file or directory path

Options:
  -h, --help               Show this help message

Description:
  Move or rename files and directories in Google Drive.
  If destination is a directory, the source will be moved into it.
  If destination doesn't exist, the source will be renamed.

Examples:
  mv old.txt new.txt       Rename a file
  mv file.txt ~/docs/      Move file to another directory
  mv dir1 dir2             Rename a directory
  mv ~/temp/file.txt .     Move file to current directory
"""
        print(help_text)
            