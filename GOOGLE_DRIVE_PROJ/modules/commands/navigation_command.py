"""
Navigation commands (pwd, cd)
从file_core.py迁移而来
"""

import time


class NavigationCommand:
    """导航命令"""
    
    def __init__(self, main_instance):
        self.main_instance = main_instance
        self.drive_service = main_instance.drive_service
    
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
            path = self.main_instance.path_resolver._convert_local_path_to_remote(path)
            
            # 使用新的路径解析器计算绝对路径
            current_shell_path = current_shell.get("current_path", "~")
            absolute_path = self.main_instance.path_resolver.compute_absolute_path(current_shell_path, path)
            
            # 使用统一的cmd_ls接口检测目录是否存在
            ls_result = self.main_instance.cmd_ls(absolute_path)
            
            if not ls_result.get('success'):
                # 添加调试信息，显示路径计算过程
                return {"success": False, "error": f"Directory does not exist: {path} (resolved to: {absolute_path})"}
            
            # 如果ls成功，说明目录存在，使用resolve_path获取目标ID和路径
            # 使用规范化后的绝对路径进行解析
            target_id, target_path = self.main_instance.resolve_path(absolute_path, current_shell)
            
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

