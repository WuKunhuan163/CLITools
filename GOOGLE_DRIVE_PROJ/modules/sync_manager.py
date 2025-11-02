#!/usr/bin/env python3
"""
Google Drive Shell - Sync Manager Module
"""

import os
import json
import shutil
from pathlib import Path
from .command_executor import debug_print
from .system_utils import is_run_environment, write_to_json_output
from .drive_api_service import test_drive_folder_access, extract_folder_id_from_url

class SyncManager:
    """Google Drive Shell Sync Manager"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance

    def move_to_local_equivalent(self, file_path, target_path="."):
        """
        将文件移动到 LOCAL_EQUIVALENT 目录，如果有同名文件则重命名
        
        Args:
            file_path (str): 要移动的文件路径
            target_path (str): 目标路径（用于检查远程文件冲突）
            
        Returns:
            dict: 包含成功状态和移动后文件路径的字典
        """
        try:
            # 确保 LOCAL_EQUIVALENT 目录存在
            local_equiv_path = Path(self.main_instance.LOCAL_EQUIVALENT)
            if not local_equiv_path.exists():
                return {"success": False, "error": f"LOCAL_EQUIVALENT directory does not exist: {self.main_instance.LOCAL_EQUIVALENT}"}
            
            source_path = Path(file_path)
            if not source_path.exists():
                return {"success": False, "error": f"File does not exist: {file_path}"}
            
            # 获取文件名和扩展名
            filename = source_path.name
            name_part = source_path.stem
            ext_part = source_path.suffix
            
            # 检查目标目录中是否已存在同名文件
            local_target_path = local_equiv_path / filename
            final_filename = filename
            renamed = False
            
            # 首先检查远端是否有同名文件和缓存建议
            debug_print(f"Checking conflicts for: {filename}")
            # 构建完整的远程路径进行验证
            if target_path == "." or target_path == "":
                remote_file_path = filename
            else:
                remote_file_path = f"{target_path}/{filename}"
            
            verify_result = self.main_instance.validation.verify_with_ls(
                path=remote_file_path,
                creation_type="file",
                max_attempts=1
            )
            remote_has_same_file = verify_result.get("success", False)
            
            # 检查是否在删除时间缓存中（5分钟内删除过）
            cache_suggests_rename = self.main_instance.cache_manager.should_rename_file(filename)
            
            debug_print(f"Conflict check: {filename} -> remote_exists={remote_has_same_file}, cache_suggests_rename={cache_suggests_rename}, local_exists={local_target_path.exists()}")
            
            # 如果远端有同名文件或缓存建议重命名，使用重命名策略
            if remote_has_same_file or cache_suggests_rename:
                debug_print(f"Need to rename {filename} to avoid conflict")
                
                # 生成新的文件名：name_1.ext, name_2.ext, ...
                counter = 1
                while True:
                    new_filename = f"{name_part}_{counter}{ext_part}"
                    new_local_target_path = local_equiv_path / new_filename
                    
                    # 检查新文件名是否在本地不冲突，并且不在缓存记录中
                    if not new_local_target_path.exists():
                        temp_cache_suggests_rename = self.main_instance.cache_manager.should_rename_file(new_filename)
                        if not temp_cache_suggests_rename:
                            local_target_path = new_local_target_path
                            final_filename = new_filename
                            renamed = True
                            debug_print(f"Found available temp filename: {new_filename}")
                            break
                        else:
                            debug_print(f"Temp filename {new_filename} also in cache, trying next")
                    
                    counter += 1
                    if counter > 100:  # 防止无限循环
                        return {
                            "success": False,
                            "error": f"Cannot generate unique filename for {filename} after 100 attempts"
                        }
                
                if cache_suggests_rename:
                    debug_print(f"Renamed based on deletion cache: {filename} -> {final_filename}")
                else:
                    debug_print(f"Renamed to avoid remote conflict: {filename} -> {final_filename}")
            
            elif local_target_path.exists():
                # 本地存在同名文件，但远端没有且缓存无风险，删除本地旧文件
                try:
                    local_target_path.unlink()
                    debug_print(f"Deleted old local file: {filename} (no remote conflict)")
                    
                    # 注意：不在这里添加删除记录，删除记录应该在文件成功上传后添加
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to delete old file: {e}"
                    }
            
            # 复制文件而不是移动（保留原文件）
            shutil.copy2(str(source_path), str(target_path))
            
            return {
                "success": True,
                "original_path": str(source_path),
                "new_path": str(target_path),
                "filename": final_filename,
                "original_filename": filename,
                "renamed": renamed
            }
            
        except Exception as e:
            return self.handle_exception(e, "Moving file")

    def check_network_connection(self):
        """
        检测网络连接状态
        
        Returns:
            dict: 网络连接状态
        """
        result = self.drive_service.test_connection()
        if result.get('success'):
            return self.create_success_result("Google Drive API connection is normal")
        else:
            return {"success": False, "error": f"Google Drive API connection failed: {result.get('error', 'Unknown error')}"}
            
    def calculate_timeout_from_file_sizes(self, file_moves):
        """
        根据文件大小计算超时时间
        
        Args:
            file_moves (list): 文件移动信息列表
            
        Returns:
            int: 超时时间（秒）
        """
        total_size_mb = 0
        for file_info in file_moves:
            file_path = file_info["new_path"]
            if os.path.exists(file_path):
                size_bytes = os.path.getsize(file_path)
                size_mb = size_bytes / (1024 * 1024)  # 转换为MB
                total_size_mb += size_mb
        
        # 基础检测时间30秒 + 按照100KB/s的速度计算文件传输时间
        # 100KB/s = 0.1MB/s，所以每MB需要10秒
        base_time = 30
        transfer_time = max(30, int(total_size_mb * 10))
        timeout = base_time + transfer_time
        return timeout

    def wait_for_file_sync(self, expected_files, file_moves):
        """
        等待文件同步到 DRIVE_EQUIVALENT 目录，使用GDS ls命令检测
        支持Ctrl+C中断
        
        Args:
            expected_files (list): 期望同步的文件名列表
            file_moves (list): 文件移动信息列表（用于计算超时时间）
            
        Returns:
            dict: 同步状态，包含cancelled字段
        """
        try:
            # 根据文件大小计算超时时间
            timeout = self.calculate_timeout_from_file_sizes(file_moves)
            max_attempts = int(timeout)  # 每秒检查一次
            
            # 定义检查函数
            def check_sync_status():
                if hasattr(self.main_instance, 'drive_service') and self.main_instance.drive_service:
                    ls_result = self.main_instance.drive_service.list_files(
                        folder_id=self.main_instance.DRIVE_EQUIVALENT_FOLDER_ID, 
                        max_results=100
                    )
                else:
                    return False  # Drive service不可用，继续等待
                
                if ls_result.get("success"):
                    files = ls_result.get("files", [])
                    current_synced = []
                    
                    for filename in expected_files:
                        # 检查文件名是否在DRIVE_EQUIVALENT中
                        file_found = any(f.get("name") == filename for f in files)
                        if file_found:
                            current_synced.append(filename)
                    
                    # 如果所有文件都已同步，返回成功
                    if len(current_synced) == len(expected_files):
                        return True  # 同步完成
                
                return False  # 继续等待
            
            # 使用统一的可中断进度循环
            from .progress_manager import interruptible_progress_loop
            result = interruptible_progress_loop(
                progress_message="⏳ Waiting for file sync ...",
                loop_func=check_sync_status,
                check_interval=1.0,
                max_attempts=max_attempts
            )
            
            if result["cancelled"]:
                return {
                    "success": False,
                    "cancelled": True,
                    "synced_files": [],
                    "sync_time": 0,
                    "error": "File sync cancelled by user"
                }
            elif result["success"]:
                return {
                    "success": True,
                    "cancelled": False,
                    "synced_files": expected_files,
                    "sync_time": result["attempts"],  # 大约的同步时间
                    "base_sync_time": result["attempts"]
                }
            else:
                # 超时失败，但不是取消
                return {
                    "success": False,
                    "cancelled": False,
                    "synced_files": [],
                    "sync_time": timeout,
                    "error": f"File sync timeout after {timeout} seconds"
                }
                
        except Exception as e:
            return {
                "success": False,
                "cancelled": False,
                "synced_files": [],
                "sync_time": 0,
                "error": f"File sync error: {str(e)}"
            }

def get_sync_config_file():
    """获取同步配置文件路径"""
    # 从modules目录向上两级到bin目录，然后进入GOOGLE_DRIVE_DATA
    data_dir = Path(__file__).parent.parent.parent / "GOOGLE_DRIVE_DATA"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "sync_config.json"

def load_sync_config():
    """加载同步配置"""
    try:
        config_file = get_sync_config_file()
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "local_equivalent": os.path.expanduser("~/Applications/Google Drive"),
                "drive_equivalent": "/content/drive/Othercomputers/我的 MacBook Air/Google Drive",
                "drive_equivalent_folder_id": "1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY"
            }
    except Exception as e:
        print(f"加载同步配置失败: {e}")
        return {
            "local_equivalent": os.path.expanduser("~/Applications/Google Drive"),
            "drive_equivalent": "/content/drive/Othercomputers/我的 MacBook Air/Google Drive", 
            "drive_equivalent_folder_id": "1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY"
        }

def save_sync_config(config):
    """保存同步配置"""
    try:
        config_file = get_sync_config_file()
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存同步配置失败: {e}")
        return False

def set_local_sync_dir(command_identifier=None):
    """设置本地同步目录"""
    try:
        # 加载当前配置
        config = load_sync_config()
        current_local = config.get("local_equivalent", "未设置")
        
        if is_run_environment(command_identifier):
            # RUN环境下返回交互式设置信息
            write_to_json_output({
                "success": True,
                "action": "interactive_setup",
                "current_local_equivalent": current_local,
                "instructions": "请在终端中运行: GOOGLE_DRIVE --desktop --set-local-sync-dir"
            }, command_identifier)
            return 0
        
        print(f"设置本地同步目录")
        print(f"=" * 50)
        print(f"当前设置: {current_local}")
        print()
        
        new_path = get_multiline_user_input("请输入新的本地同步目录路径 (直接回车保持不变): ", single_line=True)
        
        if not new_path:
            print(f"Keep current setting")
            return 0
        
        # 展开路径
        expanded_path = os.path.expanduser(os.path.expandvars(new_path))
        
        # 检查路径是否存在
        if not os.path.exists(expanded_path):
            print(f"Error: Path does not exist: {expanded_path}")
            print(f"请确认路径正确后重试")
            return 1
        
        if not os.path.isdir(expanded_path):
            print(f"Error: Path is not a directory: {expanded_path}")
            return 1
        
        # 更新配置
        config["local_equivalent"] = expanded_path
        
        if save_sync_config(config):
            print(f"Local sync directory updated: {expanded_path}")
            return 0
        else:
            print(f"Error:  Save configuration failed")
            return 1
            
    except KeyboardInterrupt:
        print(f"\nError: Operation cancelled")
        return 1
    except Exception as e:
        error_msg = f"Error setting local sync directory: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(f"Error: {error_msg}")
        return 1

def set_global_sync_dir(command_identifier=None):
    """设置全局同步目录"""
    try:
        # 加载当前配置
        config = load_sync_config()
        current_drive = config.get("drive_equivalent", "未设置")
        current_folder_id = config.get("drive_equivalent_folder_id", "未设置")
        
        if is_run_environment(command_identifier):
            # RUN环境下返回交互式设置信息
            write_to_json_output({
                "success": True,
                "action": "interactive_setup",
                "current_drive_equivalent": current_drive,
                "current_folder_id": current_folder_id,
                "instructions": "请在终端中运行: GOOGLE_DRIVE --desktop --set-global-sync-dir"
            }, command_identifier)
            return 0
        
        print(f"设置全局同步目录")
        print(f"=" * 50)
        print(f"当前设置:")
        print(f"  逻辑路径: {current_drive}")
        print(f"  文件夹ID: {current_folder_id}")
        print()
        
        # 获取文件夹URL
        folder_url = get_multiline_user_input("请输入Google Drive文件夹链接 (直接回车保持不变): ", single_line=True)
        
        if not folder_url:
            print(f"Keep current setting")
            return 0
        
        # 提取文件夹ID
        folder_id = extract_folder_id_from_url(folder_url)
        if not folder_id:
            print(f"Error: Unable to extract folder ID from URL")
            print(f"请确认URL格式正确，例如: https://drive.google.com/drive/u/0/folders/1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY")
            return 1
        
        print(f"Extracted folder ID: {folder_id}")
        
        # 测试文件夹访问
        print(f"测试文件夹访问权限...")
        if not test_drive_folder_access(folder_id):
            print(f"Error: Unable to access the folder")
            print(f"请确认:")
            print(f"  1. 文件夹ID正确")
            print(f"  2. 服务账户有访问权限")
            print(f"  3. 网络连接正常")
            return 1
        
        print(f"Folder access test passed")
        
        # 获取逻辑路径
        logical_path = get_multiline_user_input("请输入该文件夹对应的逻辑路径 (例如: /content/drive/Othercomputers/我的 MacBook Air/Google Drive): ", single_line=True)
        
        if not logical_path:
            print(f"Error: Logical path cannot be empty")
            return 1
        
        # 验证逻辑路径格式
        if not logical_path.startswith('/'):
            print(f"Warning: 逻辑路径通常以 / 开头")
        
        print(f"逻辑路径已设置为: {logical_path}")
        
        # 更新配置
        config["drive_equivalent"] = logical_path
        config["drive_equivalent_folder_id"] = folder_id
        
        if save_sync_config(config):
            print(f"Global sync directory configuration updated:")
            print(f"  文件夹ID: {folder_id}")
            print(f"  逻辑路径: {logical_path}")
            
            # 更新GoogleDriveShell实例的配置
            try:
                from ..google_drive_shell import GoogleDriveShell
                shell = GoogleDriveShell()
                shell.DRIVE_EQUIVALENT = logical_path
                shell.DRIVE_EQUIVALENT_FOLDER_ID = folder_id
                print(f"Runtime configuration also updated")
            except:
                pass  # 如果更新失败也不影响主要功能
            
            return 0
        else:
            print(f"Error:  Save configuration failed")
            return 1
            
    except KeyboardInterrupt:
        print(f"\nError: Operation cancelled")
        return 1
    except Exception as e:
        error_msg = f"Error setting global sync directory: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(f"Error: {error_msg}")
        return 1

def get_google_drive_status(command_identifier=None):
    """获取Google Drive Desktop状态信息"""
    try:
        # 导入需要的函数（延迟导入避免循环依赖）
        from . import drive_process_manager
        
        running = drive_process_manager.is_google_drive_running()
        processes = drive_process_manager.get_google_drive_processes()
        
        result_data = {
            "success": True,
            "running": running,
            "process_count": len(processes),
            "processes": processes,
            "message": f"Google Drive {'正在运行' if running else '未运行'} ({len(processes)} 个进程)"
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(result_data, command_identifier)
        else:
            print(result_data["message"])
            if running and processes:
                print(f"进程ID: {', '.join(processes)}")
        return 0
        
    except Exception as e:
        error_data = {
            "success": False,
            "error": f"获取状态时出错: {e}"
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(error_data["error"])
        return 1
