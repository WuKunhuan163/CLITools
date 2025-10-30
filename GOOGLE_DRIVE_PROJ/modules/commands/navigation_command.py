"""
Navigation commands (pwd, cd)
从file_core.py迁移而来
合并了cd_command和pwd_command
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
        if not args:
            print("Error: cd command needs a directory path")
            return 1
        
        path = args[0]
        
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
        try:
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
            
        except Exception as e:
            return {"success": False, "error": f"获取当前路径时出错: {e}"}
    
    def cmd_cd(self, path):
        """切换目录"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            if not path:
                path = "~"
            
            # 转换bash扩展的本地路径为远程路径格式
            path = self.main_instance.path_resolver.undo_local_path_user_expansion(path)
            
            # 使用新的路径解析器计算绝对路径（逻辑路径格式）
            absolute_path = self.main_instance.path_resolver.resolve_remote_absolute_path(path, current_shell, return_logical=True)
            
            # 使用统一的cmd_ls接口检测目录是否存在
            ls_result = self.main_instance.cmd_ls(absolute_path)
            
            if not ls_result.get('success'):
                # 添加调试信息，显示路径计算过程
                return {"success": False, "error": f"Directory does not exist: {path} (resolved to: {absolute_path})"}
            
            # 如果ls成功，说明目录存在，使用resolve_drive_id获取目标ID和路径
            # 使用规范化后的绝对路径进行解析
            target_id, target_path = self.main_instance.resolve_drive_id(absolute_path, current_shell)
            
            if not target_id:
                return {"success": False, "error": f"Directory does not exist: {path} (resolved path failed)"}
            
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
                
        except Exception as e:
            return {"success": False, "error": f"Execute cd command failed: {e}"}
