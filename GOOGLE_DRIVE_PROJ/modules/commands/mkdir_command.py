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
        
        # 解析绝对路径
        absolute_path = self.main_instance.resolve_remote_absolute_path(target_path, current_shell)
        if not absolute_path:
            return {"success": False, "error": f"Cannot resolve path: {target_path}"}
        
        # 生成远端mkdir命令，添加清屏和成功/失败提示（总是使用-p确保父目录存在）
        remote_command = f'mkdir -p "{absolute_path}"'
        execution_result = self.main_instance.execute_command_interface("bash", ["-c", remote_command])
        
        if not execution_result.get("success"):
            error_msg = execution_result.get('error', 'Command execution failed')
            raise RuntimeError(f"mkdir command execution failed: {error_msg}")
        
        data = execution_result.get("data", {})
        exit_code = data.get("exit_code", execution_result.get("exit_code", -1))
        if exit_code != 0:
            stderr = data.get("stderr", execution_result.get("stderr", ""))
            raise RuntimeError(f"mkdir command failed with exit code {exit_code}: {stderr}")
        
        verification_result = self.main_instance.verify_creation_with_ls(target_path, current_shell, creation_type="dir")
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
        # print(f"DEBUG in MkdirCommand: Processing mkdir with args: {args}")
        
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
