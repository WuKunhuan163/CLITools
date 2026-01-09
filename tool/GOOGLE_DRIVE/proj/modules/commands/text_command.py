"""
Text operations commands (cat, read)
"""

from .base_command import BaseCommand

class TextCommand(BaseCommand):
    """文本操作命令 - 统一处理cat, read"""
    
    @property
    def command_name(self):
        # 返回主命令名，但这个类会注册多个命令
        return "text"
    
    def execute(self, cmd, args, command_identifier=None):
        """根据命令名分发到具体的处理方法"""
        if cmd == "cat":
            return self.execute_cat(args)
        elif cmd == "read":
            return self.execute_read(args)
        else:
            print(f"Error: Unknown text command: {cmd}")
            return 1
    
    def execute_cat(self, args):
        """执行cat命令"""
        # 检查是否请求帮助
        if '--help' in args or '-h' in args:
            self.show_cat_help()
            return 0
        
        if not args:
            print("Error: cat command needs a file name")
            return 1
        
        filename = args[0]
        
        # 调用shell的cat方法
        result = self.cmd_cat(filename)
        
        if result.get("success", False):
            if not result.get("direct_feedback", False):
                print(result.get("output", ""), end = "")
            return 0
        else:
            print(result.get("error", "Failed to read file"))
            return 1
    
    def execute_read(self, args):
        """执行read命令"""
        # 检查是否请求帮助
        if '--help' in args or '-h' in args:
            self.show_read_help()
            return 0
        
        if not args:
            print("Error: read command needs a file name")
            return 1
        
        # 解析参数
        force = False
        read_args = []
        
        for arg in args:
            if arg == '--force':
                force = True
            else:
                read_args.append(arg)
        
        if not read_args:
            print("Error: read command needs a file name")
            return 1
        
        filename = read_args[0]
        remaining_args = read_args[1:]
        
        # 调用shell的read方法
        result = self.cmd_read(filename, *remaining_args, force=force)
        
        if result.get("success", False):
            if not result.get("direct_feedback", False):
                # 添加行号显示，根据总行数动态调整宽度
                content = result.get("output", "")
                lines = content.split('\n')
                total_lines = len(lines)
                width = len(str(total_lines))  # 计算总行数的位数
                for i, line in enumerate(lines, 1):
                    print(f"{i:{width}}: {line}")
            return 0
        else:
            print(result.get("error", "Failed to read file"))
            return 1


    def cmd_cat(self, filename, command_name="cat"):
        """cat命令 - 显示文件内容
        
        Args:
            filename: 要显示的文件名
            command_name: 命令名称（用于错误信息，默认"cat"）
        """
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API service not initialized"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell"}
            
            if not filename:
                return {"success": False, "error": "Please specify the file to view"}
            
            # 处理绝对远程路径，转换为逻辑路径格式
            remote_root_path = self.main_instance.REMOTE_ROOT
            remote_env_path = self.main_instance.REMOTE_ENV
            
            if filename.startswith(remote_root_path + "/"):
                # 转换为逻辑路径格式 (~/...)
                relative_part = filename[len(remote_root_path) + 1:]
                filename = f"~/{relative_part}"
            elif filename == remote_root_path:
                filename = "~"
            elif filename.startswith(remote_env_path + "/"):
                # 转换为逻辑路径格式 (@/...)
                relative_part = filename[len(remote_env_path) + 1:]
                filename = f"@/{relative_part}"
            elif filename == remote_env_path:
                filename = "@"
            
            # 分离目录路径和文件名
            import os
            if '/' in filename:
                # 包含路径分隔符，分离目录和文件名
                dir_path = os.path.dirname(filename)
                target_filename = os.path.basename(filename)
                
                # 解析目录路径获取folder_id
                folder_id, _ = self.main_instance.resolve_drive_id(dir_path, current_shell)
                
                if not folder_id:
                    return {"success": False, "error": f"{command_name}: {dir_path}: No such file or directory"}
            else:
                # 简单文件名，使用当前目录
                folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
                target_filename = filename
            
            # 使用retrieve_content API读取文件内容
            result = self.drive_service.retrieve_content(folder_id, target_filename)
            
            if result.get('success'):
                return {"success": True, "output": result['content'], "filename": filename}
            else:
                error_msg = result.get('error', 'Failed to read file')
                # 如果是文件不存在的错误，添加命令名前缀
                if 'No such file or directory' in error_msg or 'not found' in error_msg.lower():
                    error_msg = f"{command_name}: {filename}: {error_msg}"
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            return {"success": False, "error": f"执行cat命令时出错: {e}"}
    
    def cmd_read(self, filename, *remaining_args, force=False):
        """read命令 - 显示文件内容(带行号)
        
        Args:
            filename: 文件名
            remaining_args: 可选的start和end行号
            force: 是否强制重新读取（使用远程cat命令，绕过缓存）
        """
        # 如果使用--force选项，通过远程cat命令读取
        if force:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            # 解析路径为绝对路径
            absolute_path = self.main_instance.path_resolver.resolve_remote_absolute_path(
                filename, current_shell, return_logical=False
            )
            if not absolute_path:
                return {"success": False, "error": f"Could not resolve path: {filename}"}
            
            # 使用远程cat命令
            cat_cmd = f'cat "{absolute_path}"'
            cat_result = self.main_instance.execute_command_interface(cat_cmd)
            
            if not cat_result.get("success"):
                return {
                    "success": False,
                    "error": f"read: {filename}: {cat_result.get('error', 'No such file or directory')}"
                }
            
            return {"success": True, "output": cat_result.get("stdout", ""), "filename": filename}
        else:
            # 正常使用Google Drive API读取
            return self.cmd_cat(filename)
    
    def show_cat_help(self):
        """显示cat命令的帮助信息"""
        help_text = """cat - display file contents

Usage:
  cat <file>
  cat > <file> << EOF        Write multi-line content using heredoc
  cat >> <file> << EOF       Append multi-line content using heredoc

Arguments:
  file                     File path to display

Heredoc Syntax:
  cat > file.txt << "EOF"
  line 1
  line 2
  EOF

Options:
  -h, --help               Show this help message

Examples:
  cat file.txt             Display file contents
  cat ~/docs/readme.md     Display file with full path
  cat > output.txt << EOF  Write multi-line content
  First line
  Second line
  EOF
"""
        print(help_text)
    
    def show_read_help(self):
        """显示read命令的帮助信息"""
        help_text = """read - display file contents with line numbers

Usage:
  read <file> [start] [end] [options]

Arguments:
  file                     File path to display
  start                    Starting line number (optional)
  end                      Ending line number (optional)

Options:
  --force                  Force re-read (bypass cache)
  -h, --help               Show this help message

Examples:
  read file.txt            Display entire file with line numbers
  read file.txt 10 20      Display lines 10-20
  read --force file.txt    Force re-read file
"""
        print(help_text)
