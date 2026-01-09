from .base_command import BaseCommand

class MkdirCommand(BaseCommand):
    @property
    def command_name(self):
        return "mkdir"
    
    def cmd_mkdir(self, target_path, recursive=False):
        """
        通过远端命令创建目录的接口（使用统一接口）
        
        Args:
            target_path (str): 目标路径
            recursive (bool): 是否递归创建
            
        Returns:
            dict: 创建结果
        """
        # 获取当前shell以解析相对路径
        current_shell = self.main_instance.get_current_shell()
        if not current_shell:
            return {"success": False, "error": "No active remote shell"}
        
        # 路径已经在execute_shell_command中统一处理，直接使用
        absolute_path = target_path
        
        # 生成远端mkdir命令，根据recursive参数决定是否使用-p选项
        if recursive:
            remote_command = f'mkdir -p "{absolute_path}"'
        else:
            remote_command = f'mkdir "{absolute_path}"'
        execution_result = self.main_instance.execute_command_interface("bash", ["-c", remote_command])
        
        if not execution_result.get("success"):
            return execution_result
        
        data = execution_result.get("data", {})
        exit_code = data.get("exit_code", execution_result.get("exit_code", -1))
        if exit_code != 0:
            stderr = data.get("stderr", execution_result.get("stderr", ""))
            return {
                "success": False,
                "error": stderr.strip(),
                "exit_code": exit_code,
                "stderr": stderr
            }
        
        verification_result = self.main_instance.verify_with_ls(target_path, current_shell, creation_type="dir")
        if not verification_result["success"]:
            # 验证失败
            return {
                "success": False,
                "error": f"Directory creation may have failed, verification timeout: {target_path}",
                "verification": verification_result,
                "remote_command": remote_command
            }
        
        return {
            "success": True,
            "path": target_path,
            "absolute_path": absolute_path,
            "remote_command": remote_command,
            "message": "", 
            "verification": verification_result
        }
    
    def execute(self, cmd, args, command_identifier=None):
        """执行mkdir命令"""
        # 检查是否请求帮助
        if args and (args[0] == '--help' or args[0] == '-h'):
            self.show_help()
            return 0
        
        if not args:
            print("Error: mkdir command needs a directory name")
            return 1
        
        # 解析参数
        create_parents = False
        directories = []
        
        for arg in args:
            if arg == '-p':
                create_parents = True
            else:
                directories.append(arg)
        
        if not directories:
            print("Error: mkdir command needs a directory name")
            return 1
        
        # 处理每个目录
        for directory in directories:
            result = self.cmd_mkdir(directory, recursive=create_parents)
            
            if not result.get("success", False):
                print(result.get("error", f"Failed to create directory: {directory}"))
                return 1
        
        return 0
    
    def show_help(self):
        """显示mkdir命令的帮助信息"""
        help_text = """mkdir - create directories

Usage:
  mkdir [options] <directory> ...

Arguments:
  directory                Directory path(s) to create

Options:
  -p                       Create parent directories as needed
  -h, --help               Show this help message

Description:
  Create directories in Google Drive.
  Use -p flag to create intermediate parent directories if they don't exist.
  Can create multiple directories at once.

Examples:
  mkdir newdir             Create a new directory
  mkdir dir1 dir2 dir3     Create multiple directories
  mkdir -p a/b/c           Create nested directories
  mkdir ~/docs/notes       Create directory with absolute path
"""
        print(help_text)
