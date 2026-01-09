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
        elif subcommand == "clear-all":
            # reset clear-all
            return self.execute_reset_clear_all(args[1:])
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
            
            # 将路径转换为逻辑路径（使用path_resolver的统一方法）
            logical_path = self.main_instance.path_resolver.resolve_remote_absolute_path(target_path, return_logical=True)
            
            # 根据逻辑路径计算绝对路径
            if logical_path == "~":
                absolute_path = self.main_instance.REMOTE_ROOT
            elif logical_path.startswith("~/"):
                relative_part = logical_path[2:]
                absolute_path = f"{self.main_instance.REMOTE_ROOT}/{relative_part}"
            elif logical_path == "@":
                absolute_path = self.main_instance.REMOTE_ENV
            elif logical_path.startswith("@/"):
                relative_part = logical_path[2:]
                absolute_path = f"{self.main_instance.REMOTE_ENV}/{relative_part}"
            else:
                return {"success": False, "error": f"Invalid path format: {target_path}"}
            
            # 加载或创建配置文件
            from ..path_constants import PathConstants
            path_constants = PathConstants()
            config_path = str(path_constants.GDS_PATH_IDS_FILE)
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
            
            # 将绝对路径转换为逻辑路径（配置文件中使用逻辑路径作为键）
            logical_path = self.main_instance.path_resolver.resolve_remote_absolute_path(target_path, return_logical=True)
            
            # 加载配置文件
            try:
                from ..path_constants import PathConstants
                path_constants = PathConstants()
                config_path = str(path_constants.GDS_PATH_IDS_FILE)
            except ImportError:
                # 回退到旧路径（向后兼容）
                config_path = os.path.expanduser("~/.gds_path_ids.json")
            if not os.path.exists(config_path):
                return {"success": False, "error": "No path ID configuration found"}
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # 检查路径是否存在
            if logical_path not in config["path_ids"]:
                return {"success": False, "error": f"Path ID not found: {logical_path}"}
            
            # 移除路径ID
            old_id = config["path_ids"][logical_path]
            del config["path_ids"][logical_path]
            config["last_updated"] = time.time()
            
            # 保存配置文件
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            return {
                "success": True,
                "message": f"Path ID removed: {logical_path} (was: {old_id})",
                "removed_path": logical_path,
                "removed_id": old_id,
                "config_path": config_path
            }
            
        except Exception as e:
            return {"success": False, "error": f"Remove failed: {str(e)}"}
    
    def execute_reset_clear_all(self, args):
        """执行reset clear-all命令"""
        if args and args[0] in ["-h", "--help"]:
            print("Usage: reset clear-all")
            print("Clear all path ID configurations and restore defaults")
            print("")
            print("This command will:")
            print("  1. Remove all existing path ID mappings")
            print("  2. Restore default IDs for ~ and @ paths")
            print("")
            print("Note: This is typically called automatically during GOOGLE_DRIVE --remount")
            return 0
        
        result = self.cmd_reset_clear_all()
        
        if result.get("success", False):
            print(result.get("message", "All path IDs cleared and defaults restored"))
            return 0
        else:
            print(f"Error: {result.get('error', 'Clear all failed')}")
            return 1
    
    def cmd_reset_clear_all(self):
        """清空所有路径ID配置并恢复默认值"""
        try:
            import json
            import os
            import time
            
            # 加载配置文件
            try:
                from ..path_constants import PathConstants
                path_constants = PathConstants()
                config_path = str(path_constants.GDS_PATH_IDS_FILE)
            except ImportError:
                # 回退到旧路径（向后兼容）
                config_path = os.path.expanduser("~/.gds_path_ids.json")
            
            # 记录清理前的状态
            old_config = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        old_config = json.load(f)
                except Exception:
                    pass
            
            old_path_count = len(old_config.get("path_ids", {}))
            
            # 创建新的配置，只包含基础结构
            new_config = {
                "path_ids": {},
                "last_updated": time.time(),
                "created": old_config.get("created", time.time()),
                "version": "2.0"
            }
            
            # 恢复默认的路径ID（如果可以获取的话）
            try:
                # 尝试获取当前的REMOTE_ROOT和REMOTE_ENV的ID
                current_shell = self.main_instance.get_current_shell()
                if current_shell:
                    # 尝试解析 ~ 路径的ID
                    try:
                        home_id, _ = self.main_instance.resolve_drive_id("~", current_shell)
                        if home_id:
                            new_config["path_ids"]["~"] = home_id
                            print(f"Restored default ID for ~: {home_id}")
                    except Exception as e:
                        print(f"Warning: Could not restore ~ ID: {e}")
                    
                    # 尝试解析 @ 路径的ID
                    try:
                        env_id, _ = self.main_instance.resolve_drive_id("@", current_shell)
                        if env_id:
                            new_config["path_ids"]["@"] = env_id
                            print(f"Restored default ID for @: {env_id}")
                    except Exception as e:
                        print(f"Warning: Could not restore @ ID: {e}")
            except Exception as e:
                print(f"Warning: Could not restore default IDs: {e}")
            
            # 确保配置目录存在
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            # 保存新配置
            with open(config_path, 'w') as f:
                json.dump(new_config, f, indent=2)
            
            restored_count = len(new_config["path_ids"])
            
            return {
                "success": True,
                "message": f"Cleared {old_path_count} path IDs and restored {restored_count} default IDs",
                "cleared_count": old_path_count,
                "restored_count": restored_count,
                "config_path": config_path,
                "restored_paths": list(new_config["path_ids"].keys())
            }
            
        except Exception as e:
            return {"success": False, "error": f"Clear all failed: {str(e)}"}
    
    def show_help(self):
        """显示帮助信息"""
        print("Reset Command Usage:")
        print("  reset id <path> <remote_id>     - Reset shell ID for specified path")
        print("  reset remove <path>             - Remove path ID configuration")
        print("  reset clear-all                 - Clear all path IDs and restore defaults")
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
        print("- Saving the mapping to GOOGLE_DRIVE_DATA/gds_path_ids.json")
        print("- Removing child path IDs to maintain hierarchy")
        print("- Updating current shell state")
        print("- Removing path ID configurations to use parent resolution")
        return 0
