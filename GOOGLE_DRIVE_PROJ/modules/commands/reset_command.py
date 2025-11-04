#!/usr/bin/env python3
"""
Reset Command - 重置shell状态和路径信息
"""

from .base_command import BaseCommand

class ResetCommand(BaseCommand):
    """重置命令处理器"""
    
    @property
    def command_name(self) -> str:
        """返回主命令名称"""
        return "reset"
    
    def get_command_names(self):
        """返回此命令处理的命令名称列表"""
        return ["reset", "reset-id"]
    
    def execute(self, command_name, args, **kwargs):
        """执行reset命令"""
        if not args:
            return self.show_help()
        
        subcommand = args[0]
        
        if subcommand == "id" or subcommand == "shell-id":
            # reset id <path> <remote_id>
            return self.execute_reset_id(args[1:])
        elif subcommand == "remove" or subcommand == "rm":
            # reset remove <path>
            return self.execute_reset_remove(args[1:])
        else:
            return self.show_help()
    
    def execute_reset_id(self, args):
        """执行reset id命令"""
        if len(args) < 2:
            print("Usage: reset id <path> <remote_id>")
            print("Examples:")
            print("  reset id ~ gds_test_20251104_193903_358412_4831496d")
            print("  reset id ~/tmp my_tmp_shell_id")
            print("  reset id @ my_env_shell_id")
            return 1
        
        target_path = args[0]
        remote_id = args[1]
        
        result = self.cmd_reset_id(target_path, remote_id)
        
        if result.get("success", False):
            print(result.get("message", "Shell ID reset completed"))
            return 0
        else:
            print(f"Error: {result.get('error', 'Reset failed')}")
            return 1
    
    def cmd_reset_id(self, target_path, remote_id):
        """重置指定路径的shell ID并保存到配置"""
        try:
            import json
            import os
            import time
            
            # 解析目标路径
            if target_path == "~":
                logical_path = "~"
                absolute_path = self.main_instance.REMOTE_ROOT
            elif target_path.startswith("~/"):
                logical_path = target_path
                relative_part = target_path[2:]
                absolute_path = f"{self.main_instance.REMOTE_ROOT}/{relative_part}"
            elif target_path == "@":
                logical_path = "@"
                absolute_path = self.main_instance.REMOTE_ENV
            elif target_path.startswith("@/"):
                logical_path = target_path
                relative_part = target_path[2:]
                absolute_path = f"{self.main_instance.REMOTE_ENV}/{relative_part}"
            else:
                return {"success": False, "error": f"Invalid path format: {target_path}"}
            
            # 加载或创建配置文件
            config_path = os.path.expanduser("~/.gds_path_ids.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {"path_ids": {}, "last_updated": None}
            
            # 移除规则：设置目录的id时，删除该目录及其子目录的id，但不删除父目录的id
            paths_to_remove = []
            for existing_path in config["path_ids"].keys():
                # 检查是否是当前路径或者当前路径的子路径
                if existing_path == logical_path or existing_path.startswith(logical_path + "/"):
                    paths_to_remove.append(existing_path)
            
            for path in paths_to_remove:
                del config["path_ids"][path]
                # print(f"Removed child path ID: {path}")
            
            # 保存新的路径ID
            old_id = config["path_ids"].get(logical_path, "none")
            config["path_ids"][logical_path] = remote_id
            config["last_updated"] = time.time()
            
            # 保存配置文件
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # 动态更新当前shell的ID（如果当前shell路径是被reset的路径或其子目录）
            current_shell = self.main_instance.get_current_shell()
            if current_shell:
                current_path = current_shell.get("current_path", "~")
                
                # 检查当前shell路径是否受影响
                if current_path == logical_path or current_path.startswith(logical_path + "/"):
                    # 更新当前shell的folder_id
                    if current_path == logical_path:
                        # 精确匹配，直接使用新ID
                        current_shell["current_folder_id"] = remote_id
                        print(f"Updated current shell folder ID to: {remote_id}")
                    else:
                        # 子路径，需要从新的父ID开始解析
                        try:
                            resolved_id, _ = self.main_instance.resolve_drive_id(current_path, current_shell)
                            if resolved_id:
                                current_shell["current_folder_id"] = resolved_id
                                print(f"Updated current shell folder ID for {current_path} to: {resolved_id}")
                        except Exception as e:
                            print(f"Warning: Could not update shell folder ID for {current_path}: {e}")
                
                # 保存shell状态
                try:
                    # 获取当前shells数据并保存
                    shells_data = self.main_instance.shell_management.load_shells()
                    self.main_instance.shell_management.save_shells(shells_data)
                except Exception as e:
                    print(f"Warning: Failed to save shell data: {e}")
            
            return {
                "success": True,
                "message": f"Reset Google Drive id for path '{logical_path}' to {remote_id} (was: {old_id})",
                "old_id": old_id,
                "new_id": remote_id,
                "path": logical_path,
                "absolute_path": absolute_path,
                "config_path": config_path,
                "removed_children": len(paths_to_remove)
            }
            
        except Exception as e:
            return {"success": False, "error": f"Reset failed: {str(e)}"}
    
    def execute_reset_remove(self, args):
        """执行reset remove命令"""
        if len(args) < 1:
            print("Usage: reset remove <path>")
            print("Examples:")
            print("  reset remove ~")
            print("  reset remove ~/tmp")
            print("  reset remove @")
            return 1
        
        target_path = args[0]
        
        result = self.cmd_reset_remove(target_path)
        
        if result.get("success", False):
            print(result.get("message", "Path ID removed"))
            return 0
        else:
            print(f"Error: {result.get('error', 'Remove failed')}")
            return 1
    
    def cmd_reset_remove(self, target_path):
        """移除指定路径的ID配置，使其使用父目录ID解析"""
        try:
            import json
            import os
            import time
            
            # 加载配置文件
            config_path = os.path.expanduser("~/.gds_path_ids.json")
            if not os.path.exists(config_path):
                return {"success": False, "error": "No path ID configuration found"}
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # 检查路径是否存在
            if target_path not in config["path_ids"]:
                return {"success": False, "error": f"Path ID not found: {target_path}"}
            
            # 移除路径ID
            old_id = config["path_ids"][target_path]
            del config["path_ids"][target_path]
            config["last_updated"] = time.time()
            
            # 保存配置文件
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            return {
                "success": True,
                "message": f"Path ID removed: {target_path} (was: {old_id})",
                "removed_path": target_path,
                "removed_id": old_id,
                "config_path": config_path
            }
            
        except Exception as e:
            return {"success": False, "error": f"Remove failed: {str(e)}"}
    
    def show_help(self):
        """显示帮助信息"""
        print("Reset Command Usage:")
        print("  reset id <path> <remote_id>     - Reset shell ID for specified path")
        print("  reset remove <path>             - Remove path ID configuration")
        print("")
        print("Examples:")
        print("  reset id ~ gds_test_20251104_193903_358412_4831496d")
        print("  reset id ~/tmp my_tmp_shell_id")
        print("  reset id @ my_env_shell_id")
        print("  reset remove ~/tmp")
        print("  reset remove @")
        print("")
        print("This command helps diagnose path detection issues by:")
        print("- Setting a specific remote shell ID for a logical path")
        print("- Saving the mapping to ~/.gds_path_ids.json")
        print("- Removing child path IDs to maintain hierarchy")
        print("- Updating current shell state")
        print("- Removing path ID configurations to use parent resolution")
        return 0
