#!/usr/bin/env python3
"""
Google Drive 文件缓存管理系统
管理远端文件的本地缓存，使用cache_config.json统一管理
"""

import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

class GDSCacheManager:
    """Google Drive Shell 缓存管理器"""
    
    def __init__(self, cache_root: str = None):
        if cache_root is None:
            cache_root = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA"
        self.cache_root = Path(cache_root)
        self.remote_files_dir = self.cache_root / "remote_files"
        self.cache_config_file = self.cache_root / "cache_config.json"
        
        # 确保目录存在
        self.cache_root.mkdir(exist_ok=True)
        self.remote_files_dir.mkdir(exist_ok=True)
        
        # 初始化配置
        self.cache_config = self._load_cache_config()
        
        # 删除旧的path_mapping.json文件（如果存在）
        old_path_mapping_file = self.cache_root / "path_mapping.json"
        if old_path_mapping_file.exists():
            old_path_mapping_file.unlink()
    
    def _load_cache_config(self) -> Dict:
        """加载缓存配置"""
        if self.cache_config_file.exists():
            with open(self.cache_config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 默认配置
        return {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "files": {}
        }
    
    def _save_cache_config(self):
        """保存缓存配置"""
        try:
            with open(self.cache_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error: Failed to save cache config: {e}")
    
    def _generate_file_hash(self, file_path: str) -> str:
        """为文件生成哈希值作为缓存文件名"""
        hasher = hashlib.sha256()
        
        # 使用远端路径和时间戳生成唯一哈希
        content = f"{file_path}_{datetime.now().isoformat()}"
        hasher.update(content.encode('utf-8'))
        
        return hasher.hexdigest()[:16]  # 使用前16位作为文件名
    
    def _get_file_content_hash(self, local_file_path: str) -> str:
        """计算文件内容的哈希值，用于检测修改"""
        hasher = hashlib.md5()
        with open(local_file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def cache_file(self, remote_path: str, temp_file_path: str) -> Dict:
        """
        缓存文件到本地
        
        Args:
            remote_path: 远端文件路径
            temp_file_path: 临时文件路径
            
        Returns:
            Dict: 缓存结果
        """
        try:
            cache_hash = self._generate_file_hash(remote_path)
            cache_file_path = self.remote_files_dir / cache_hash
            shutil.copy2(temp_file_path, cache_file_path)
            content_hash = self._get_file_content_hash(str(cache_file_path))
            cache_info = {
                "cache_file": cache_hash,
                "cache_path": str(cache_file_path),
                "content_hash": content_hash,
                "cached_time": datetime.now().isoformat(),
                "status": "valid"
            }
            
            # 检查是否有待处理的修改时间（支持多种路径格式）
            pending_modified_time = self.get_pending_modified_time(remote_path)
            current_shell = self.main_instance.get_current_shell()
            remote_path = self.main_instance.path_resolver.resolve_remote_absolute_path(remote_path, current_shell)
            self.clear_pending_modified_time(remote_path)
            if pending_modified_time:
                cache_info["remote_modified_time"] = pending_modified_time
            self.cache_config["files"][remote_path] = cache_info
            
            # 保存配置
            self._save_cache_config()
            return {
                "success": True,
                "cache_file": cache_hash,
                "cache_path": str(cache_file_path),
                "remote_path": remote_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to cache file: {e}"
            }
    
    def is_file_cached(self, remote_path: str) -> bool:
        """检查文件是否已缓存"""
        return remote_path in self.cache_config["files"]
    
    def get_cached_file(self, remote_path: str) -> Optional[Dict]:
        """获取缓存文件信息"""
        return self.cache_config["files"].get(remote_path)
    
    def get_cached_file_path(self, remote_path: str) -> Optional[str]:
        """获取缓存文件的本地路径"""
        cached_info = self.get_cached_file(remote_path)
        if cached_info:
            cache_file_path = self.remote_files_dir / cached_info["cache_file"]
            if cache_file_path.exists():
                return str(cache_file_path)
        return None
    
    def cleanup_cache(self, remote_path: str = None) -> Dict:
        """
        清理缓存
        
        Args:
            remote_path: 要清理的特定远端路径，如果为None则清理所有
            
        Returns:
            Dict: 清理结果
        """
        try:
            if remote_path:
                # 清理特定文件
                if remote_path in self.cache_config["files"]:
                    cache_info = self.cache_config["files"][remote_path]
                    cache_file_path = self.remote_files_dir / cache_info["cache_file"]
                    
                    # 删除缓存文件
                    if cache_file_path.exists():
                        cache_file_path.unlink()
                    
                    # 删除配置条目
                    del self.cache_config["files"][remote_path]
                    
                    # 保存配置
                    self._save_cache_config()
                    
                    return {
                        "success": True,
                        "cleaned_files": 1,
                        "remote_path": remote_path
                    }
                else:
                    return {
                        "success": False,
                        "error": f"File not found in cache: {remote_path}"
                    }
            else:
                # 清理所有缓存
                cleaned_count = 0
                for file_info in self.cache_config["files"].values():
                    cache_file_path = self.remote_files_dir / file_info["cache_file"]
                    if cache_file_path.exists():
                        cache_file_path.unlink()
                        cleaned_count += 1
                
                # 重置配置
                self.cache_config["files"] = {}
                self._save_cache_config()
                
                return {
                    "success": True,
                    "cleaned_files": cleaned_count
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to clean cache: {e}"
            }
    
    def get_pending_modified_time(self, remote_path: str):
        """
        获取待处理的文件修改时间
        
        Args:
            remote_path: 远端文件路径
            
        Returns:
            str or None: 修改时间字符串，如果不存在则返回None
        """
        pending_times = self.cache_config.get("pending_modified_times", {})
        if remote_path in pending_times:
            return pending_times[remote_path]["modified_time"]
        return None
    
    def clear_pending_modified_time(self, remote_path: str):
        """
        清除待处理的文件修改时间（通常在文件被缓存后调用）
        
        Args:
            remote_path: 远端文件路径
        """
        if "pending_modified_times" in self.cache_config and remote_path in self.cache_config["pending_modified_times"]:
            del self.cache_config["pending_modified_times"][remote_path]
            self._save_cache_config()
            return True
        return False

