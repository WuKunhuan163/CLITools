#!/usr/bin/env python3
"""
Google Drive Shell Cache Manager Module
"""

import json
import time
from .command_executor import debug_print
import hashlib
from pathlib import Path
from typing import Dict

class CacheManager:
    """Google Drive Shell Cache Manager"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance

    def get_local_cache_path(self, remote_path):
        """获取远程文件对应的本地缓存路径"""
        from cache_manager import GDSCacheManager
        cache_manager = GDSCacheManager()
        file_hash = hashlib.md5(remote_path.encode()).hexdigest()[:16]
        local_path = cache_manager.remote_files_dir / file_hash
        if local_path.exists():
            return str(local_path)
        else:
            return file_hash

    def cleanup_local_equivalent_files(self, file_moves):
        """
        清理LOCAL_EQUIVALENT中的文件（上传完成后）
        
        Args:
            file_moves (list): 文件移动信息列表
        """
        try:
            cleaned_files = []
            failed_cleanups = []
            for file_info in file_moves:
                filename = file_info["filename"]  # 实际的文件名（可能已重命名）
                file_path = Path(file_info["new_path"])
                
                try:
                    if file_path.exists():
                        file_path.unlink()
                        cleaned_files.append(filename)
                        original_filename = file_info.get("original_filename", filename)
                        self.add_deletion_record(original_filename)
                    else:
                        debug_print(f"File already deleted: {filename} (skipped)")
                except Exception as e:
                    failed_cleanups.append({"file": filename, "error": str(e)})
                    print(f"Failed to clean file: {filename} - {e}")
            
            if cleaned_files:
                pass
            
            if failed_cleanups:
                pass
                
        except Exception as e:
            print(f"Error cleaning LOCAL_EQUIVALENT files: {e}")

    def load_deletion_cache(self):
        """
        加载删除时间缓存
        
        Returns:
            list: 删除记录栈（按时间排序）
        """
        try:
            if self.main_instance.deletion_cache_file.exists():
                with open(self.main_instance.deletion_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    return cache_data.get("deletion_records", [])
            else:
                return []
        except Exception as e:
            print(f"Warning: Load deletion cache failed: {e}")
            return []

    def save_deletion_cache(self, deletion_records):
        """
        保存删除时间缓存
        
        Args:
            deletion_records (list): 删除记录栈
        """
        try:
            cache_data = {
                "deletion_records": deletion_records,
                "last_updated": time.time()
            }
            with open(self.main_instance.deletion_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Save deletion cache failed: {e}")
    
    def should_rename_file(self, filename):
        """
        检查是否应该重命名文件（基于删除缓存）
        
        Args:
            filename (str): 文件名
            
        Returns:
            bool: 是否应该重命名
        """
        try:
            deletion_records = self.load_deletion_cache()
            current_time = time.time()
            
            # 添加调试信息
            from .command_executor import debug_print
            debug_print(f"Checking rename for {filename}: found {len(deletion_records)} deletion records")
            
            # 检查5分钟内是否删除过同名文件
            for record in deletion_records:
                record_filename = record.get("filename", "")
                record_timestamp = record.get("timestamp", 0)
                time_diff = current_time - record_timestamp
                
                debug_print(f"Record: {record_filename}, age: {time_diff:.1f}s")
                
                if (record_filename == filename and time_diff < 300):  # 5分钟 = 300秒
                    debug_print(f"Should rename {filename} (found in deletion cache, age: {time_diff:.1f}s)")
                    return True
            
            debug_print(f"No need to rename {filename} (not in recent deletion cache)")
            return False
        except Exception as e:
            print(f"Warning: Check file rename suggestion failed: {e}")
            return False
    
    def add_deletion_record(self, filename):
        """
        添加文件删除记录
        
        Args:
            filename (str): 被删除的文件名
        """
        try:
            deletion_records = self.load_deletion_cache()
            
            # 添加新的删除记录
            deletion_records.append({
                "filename": filename,
                "timestamp": time.time()
            })
            
            # 清理5分钟以前的记录
            current_time = time.time()
            deletion_records = [
                record for record in deletion_records
                if current_time - record.get("timestamp", 0) < 300
            ]
            
            # 保存更新的缓存
            self.save_deletion_cache(deletion_records)
        except Exception as e:
            print(f"Warning: Add deletion record failed: {e}")

    def load_cache_config(self):
        """加载缓存配置"""
        try:
            if self.main_instance.config_file.exists():
                with open(self.main_instance.config_file, 'r', encoding='utf-8') as f:
                    self.cache_config = json.load(f)
                    self.cache_config_loaded = True
            else:
                self.cache_config = {}
                self.cache_config_loaded = False
        except Exception as e:
            print(f"Warning: Load cache config failed: {e}")
            self.cache_config = {}
            self.cache_config_loaded = False

    def is_remote_file_cached(self, remote_path: str) -> Dict:
        """检查远端文件是否在本地有缓存"""
        try:
            from cache_manager import GDSCacheManager
            cache_manager = GDSCacheManager()
            
            cache_config = cache_manager.cache_config
            files = cache_config.get("files", {})
            
            if remote_path in files:
                file_info = files[remote_path]
                cache_file_path = file_info.get("cache_path")
                
                if cache_file_path and Path(cache_file_path).exists():
                    return {
                        "success": True,
                        "is_cached": True,
                        "cache_file_path": cache_file_path,
                        "cache_info": file_info
                    }
                else:
                    return {
                        "success": True,
                        "is_cached": False,
                        "reason": "cache_file_not_found"
                    }
            else:
                return {
                    "success": True,
                    "is_cached": False,
                    "reason": "not_in_cache_config"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Check cache failed: {e}"
            }

    def get_remote_file_modification_time(self, remote_path: str) -> Dict:
        """获取远端文件的修改时间"""
        try:
            if '/' not in remote_path and not remote_path.startswith('~'):
                result = self.main_instance.cmd_ls('', detailed=True)
                if result["success"] and result["files"]:
                    for file_info in result["files"]:
                        if file_info.get("name") == remote_path:
                            modified_time = file_info.get("modifiedTime")
                            if modified_time:
                                return {
                                    "success": True,
                                    "modified_time": modified_time,
                                    "file_info": file_info
                                }
                            else:
                                return {
                                    "success": False,
                                    "error": "Unable to get file modification time"
                                }
                    
                    # 文件未找到
                    return {
                        "success": False,
                        "error": f"File does not exist or cannot be accessed: {remote_path}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Unable to list directory content: {result.get('error', 'unknown error')}"
                    }
            else:
                # 原来的逻辑，处理路径格式的文件
                result = self.main_instance.cmd_ls(remote_path, detailed=True)
                
                if result["success"] and result["files"]:
                    file_info = result["files"][0]
                    modified_time = file_info.get("modifiedTime")
                    
                    if modified_time:
                        return {
                            "success": True,
                            "modified_time": modified_time,
                            "file_info": file_info
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Unable to get file modification time"
                        }
                else:
                    return {
                        "success": False,
                        "error": f"File does not exist or cannot be accessed: {remote_path}"
                    }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Get file modification time failed: {e}"
            }

    def is_cached_file_up_to_date(self, remote_path: str) -> Dict:
        """检查缓存文件是否为最新版本"""
        try:
            cache_result = self.is_remote_file_cached(remote_path)
            if not cache_result["success"]:
                return cache_result
            
            if not cache_result["is_cached"]:
                return {
                    "success": True,
                    "is_cached": False,
                    "is_up_to_date": False,
                    "reason": "no_cache"
                }
            
            cache_info = cache_result["cache_info"]
            cached_modified_time = cache_info.get("remote_modified_time")
            
            if not cached_modified_time:
                return {
                    "success": True,
                    "is_cached": True,
                    "is_up_to_date": False,
                    "reason": "no_cached_modified_time"
                }
            
            import os
            filename = os.path.basename(remote_path)
            remote_time_result = self.get_remote_file_modification_time(filename)
            if not remote_time_result["success"]:
                return {
                    "success": False,
                    "error": f"Unable to get remote modification time: {remote_time_result.get('error', 'unknown error')}"
                }
            
            current_modified_time = remote_time_result["modified_time"]
            is_up_to_date = cached_modified_time == current_modified_time
            
            return {
                "success": True,
                "is_cached": True,
                "is_up_to_date": is_up_to_date,
                "cached_modified_time": cached_modified_time,
                "current_modified_time": current_modified_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Check cache new or old failed: {e}"
            }
