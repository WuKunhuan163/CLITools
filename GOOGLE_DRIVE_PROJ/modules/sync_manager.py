#!/usr/bin/env python3
"""
Google Drive Shell - Sync Manager Module
从google_drive_shell.py重构而来的sync_manager模块
"""

import os
import sys
import json
import time
import hashlib
import warnings
import subprocess
import shutil
import zipfile
import tempfile
from pathlib import Path
import platform
import psutil
from typing import Dict
try:
    from ..google_drive_api import GoogleDriveService
except ImportError:
    from GOOGLE_DRIVE_PROJ.google_drive_api import GoogleDriveService

# 导入debug捕获系统
from .command_executor import debug_capture, debug_print

class SyncManager:
    """Google Drive Shell Sync Manager"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance  # 引用主实例以访问其他属性

    def move_to_local_equivalent(self, file_path):
        """
        将文件移动到 LOCAL_EQUIVALENT 目录，如果有同名文件则重命名
        
        Args:
            file_path (str): 要移动的文件路径
            
        Returns:
            dict: 包含成功状态和移动后文件路径的字典
        """
        try:
            # 确保 LOCAL_EQUIVALENT 目录存在
            local_equiv_path = Path(self.main_instance.LOCAL_EQUIVALENT)
            if not local_equiv_path.exists():
                return self._create_error_result(f"LOCAL_EQUIVALENT directory does not exist: {self.main_instance.LOCAL_EQUIVALENT}")
            
            source_path = Path(file_path)
            if not source_path.exists():
                return self._create_error_result(f"File does not exist: {file_path}")
            
            # 获取文件名和扩展名
            filename = source_path.name
            name_part = source_path.stem
            ext_part = source_path.suffix
            
            # 检查目标目录中是否已存在同名文件
            target_path = local_equiv_path / filename
            final_filename = filename
            renamed = False
            
            # 首先检查远端是否有同名文件和缓存建议
            debug_print(f"Checking conflicts for: {filename}")
            remote_check_result = self.main_instance.file_validator._check_remote_file_exists(filename)
            remote_has_same_file = remote_check_result.get("exists", False)
            
            # 检查是否在删除时间缓存中（5分钟内删除过）
            cache_suggests_rename = self.should_rename_file(filename)
            
            debug_print(f"Conflict check: {filename} -> remote_exists={remote_has_same_file}, cache_suggests_rename={cache_suggests_rename}, local_exists={target_path.exists()}")
            
            # 如果远端有同名文件或缓存建议重命名，使用重命名策略
            if remote_has_same_file or cache_suggests_rename:
                debug_print(f"🏷️  Need to rename {filename} to avoid conflict")
                
                # 生成新的文件名：name_1.ext, name_2.ext, ...
                counter = 1
                while True:
                    new_filename = f"{name_part}_{counter}{ext_part}"
                    new_target_path = local_equiv_path / new_filename
                    
                    # 检查新文件名是否在本地不冲突，并且不在缓存记录中
                    if not new_target_path.exists():
                        # 检查缓存是否建议这个临时文件名也需要重命名
                        temp_cache_suggests_rename = self.should_rename_file(new_filename)
                        if not temp_cache_suggests_rename:
                            # 找到了不冲突的文件名（本地不存在，缓存中也没有使用记录）
                            target_path = new_target_path
                            final_filename = new_filename
                            renamed = True
                            debug_print(f"🏷️  Found available temp filename: {new_filename}")
                            break
                        else:
                            debug_print(f"🏷️  Temp filename {new_filename} also in cache, trying next")
                    
                    counter += 1
                    if counter > 100:  # 防止无限循环
                        return {
                            "success": False,
                            "error": f"Cannot generate unique filename for {filename} after 100 attempts"
                        }
                
                if cache_suggests_rename:
                    debug_print(f"🏷️  Renamed based on deletion cache: {filename} -> {final_filename}")
                else:
                    debug_print(f"🏷️  Renamed to avoid remote conflict: {filename} -> {final_filename}")
            
            elif target_path.exists():
                # 本地存在同名文件，但远端没有且缓存无风险，删除本地旧文件
                try:
                    target_path.unlink()
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
            return self._handle_exception(e, "Moving file")

    def check_network_connection(self):
        """
        检测网络连接状态
        
        Returns:
            dict: 网络连接状态
        """
        try:
            # 如果有可用的API服务，直接测试API连接
            if self.drive_service:
                try:
                    # 尝试一个简单的API调用
                    result = self.drive_service.test_connection()
                    if result.get('success'):
                        return self._create_success_result("Google Drive API connection is normal")
                    else:
                        return {"success": False, "error": f"Google Drive API connection failed: {result.get('error', 'Unknown error')}"}
                except Exception as e:
                    # API测试失败，继续尝试ping
                    pass
            
            # 回退到ping测试（更宽松的参数）
            import platform
            if platform.system() == "Darwin":  # macOS
                ping_cmd = ["ping", "-c", "1", "-W", "3000", "8.8.8.8"]  # 使用Google DNS
            else:
                ping_cmd = ["ping", "-c", "1", "-W", "3", "8.8.8.8"]
            
            result = subprocess.run(
                ping_cmd, 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                return self._create_success_result("Network connection is normal")
            else:
                # 网络测试失败但不影响功能
                return {"success": True, "message": "Network status unknown, but will continue"}
                
        except subprocess.TimeoutExpired:
            return {"success": True, "message": "Network detection timeout, but will continue"}
        except Exception as e:
            return {"success": True, "message": f"Network detection failed, but will continue: {e}"}

    def calculate_timeout_from_file_sizes(self, file_moves):
        """
        根据文件大小计算超时时间
        
        Args:
            file_moves (list): 文件移动信息列表
            
        Returns:
            int: 超时时间（秒）
        """
        try:
            total_size_mb = 0
            for file_info in file_moves:
                file_path = file_info["new_path"]
                if os.path.exists(file_path):
                    size_bytes = os.path.getsize(file_path)
                    size_mb = size_bytes / (1024 * 1024)  # 转换为MB
                    total_size_mb += size_mb
            
            # 基础检测时间30秒 + 按照100KB/s的速度计算文件传输时间
            # 100KB/s = 0.1MB/s，所以每MB需要10秒
            base_time = 30  # 基础检测时间（从10秒增加到30秒）
            transfer_time = max(30, int(total_size_mb * 10))  # 按100KB/s计算，最少30秒（从10秒增加到30秒）
            timeout = base_time + transfer_time
            
            return timeout
            
        except Exception as e:
            debug_print(f"Error calculating timeout: {e}")
            return 60  # 默认60秒（10秒基础 + 50秒传输）

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
                # 直接使用Google Drive API检查DRIVE_EQUIVALENT目录
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
    
    def _create_error_result(self, error_message):
        """
        创建标准的错误返回结果
        
        Args:
            error_message (str): 错误消息
            
        Returns:
            dict: 标准错误结果字典
        """
        return {"success": False, "error": error_message}
    
    def _handle_exception(self, e, operation_name, default_message=None):
        """
        通用异常处理方法
        
        Args:
            e (Exception): 异常对象
            operation_name (str): 操作名称
            default_message (str, optional): 默认错误消息
            
        Returns:
            dict: 错误结果字典
        """
        if default_message:
            error_msg = f"{default_message}: {str(e)}"
        else:
            error_msg = f"{operation_name}时出错: {str(e)}"
        return self._create_error_result(error_msg)
    

    def should_rename_file(self, filename):
        """委托到cache_manager的文件重命名检查"""
        return self.main_instance.cache_manager.should_rename_file(filename)
    
    def add_deletion_record(self, filename):
        """委托到cache_manager的删除记录添加"""
        return self.main_instance.cache_manager.add_deletion_record(filename)
