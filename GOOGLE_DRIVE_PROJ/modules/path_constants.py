#!/usr/bin/env python3
"""
统一的路径常量管理器

集中管理所有路径相关的常量，避免重复定义。
提供统一的路径解析和配置加载功能。
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


class PathConstants:
    """路径常量管理器"""
    
    def __init__(self):
        # 基础路径常量
        self.HOME_DIR = Path.home()
        self.BIN_DIR = self.HOME_DIR / ".local/bin"
        self.GOOGLE_DRIVE_PROJ_DIR = self.BIN_DIR / "GOOGLE_DRIVE_PROJ"
        self.GOOGLE_DRIVE_DATA_DIR = self.BIN_DIR / "GOOGLE_DRIVE_DATA"
        
        # 确保目录存在
        self.GOOGLE_DRIVE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # 配置文件路径
        self.SYNC_CONFIG_FILE = self.GOOGLE_DRIVE_DATA_DIR / "sync_config.json"
        self.SHELLS_FILE = self.GOOGLE_DRIVE_DATA_DIR / "shells.json"
        self.CACHE_CONFIG_FILE = self.GOOGLE_DRIVE_DATA_DIR / "cache_config.json"
        self.DELETION_CACHE_FILE = self.GOOGLE_DRIVE_DATA_DIR / "deletion_cache.json"
        
        # 队列和锁文件
        self.PRIORITY_QUEUE_FILE = self.GOOGLE_DRIVE_DATA_DIR / "priority_queue.json"
        self.NORMAL_QUEUE_FILE = self.GOOGLE_DRIVE_DATA_DIR / "normal_queue.json"
        self.QUEUE_LOCK_FILE = self.GOOGLE_DRIVE_DATA_DIR / "queue_lock.lock"
        self.WINDOW_LOCK_FILE = self.GOOGLE_DRIVE_DATA_DIR / "window_lock.lock"
        self.WINDOW_PID_FILE = self.GOOGLE_DRIVE_DATA_DIR / "window_lock.pid"
        
        # 日志和调试文件
        self.ERROR_LOG_FILE = self.GOOGLE_DRIVE_DATA_DIR / "error_log.txt"
        self.RAW_GDS_OUTPUT_FILE = self.GOOGLE_DRIVE_DATA_DIR / "raw_gds_output.txt"
        
        # 默认路径值（可以被配置覆盖）
        self._default_paths = {
            "LOCAL_EQUIVALENT": str(self.HOME_DIR / "Applications/Google Drive"),
            "DRIVE_EQUIVALENT": "/content/drive/Othercomputers/我的 MacBook Air/Google Drive",
            "REMOTE_ROOT": "/content/drive/MyDrive/REMOTE_ROOT",
            "REMOTE_ENV": "/content/drive/MyDrive/REMOTE_ENV"
        }
        
        # 文件夹ID常量
        self._default_folder_ids = {
            "HOME_FOLDER_ID": "root",
            "REMOTE_ROOT_FOLDER_ID": "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f",
            "REMOTE_ENV_FOLDER_ID": None,
            "DRIVE_EQUIVALENT_FOLDER_ID": "1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY"
        }
        
        # URL常量
        self.HOME_URL = "https://drive.google.com/drive/u/0/my-drive"
        
        # 加载配置
        self._load_configuration()
    
    def _load_configuration(self):
        """加载配置文件中的路径设置"""
        try:
            if self.SYNC_CONFIG_FILE.exists():
                with open(self.SYNC_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 更新路径配置
                for key, default_value in self._default_paths.items():
                    config_key = key.lower()
                    if config_key in config:
                        self._default_paths[key] = config[config_key]
                
                # 更新文件夹ID配置
                for key, default_value in self._default_folder_ids.items():
                    config_key = key.lower()
                    if config_key in config:
                        self._default_folder_ids[key] = config[config_key]
                        
        except Exception as e:
            print(f"Warning: Failed to load path configuration: {e}")
    
    def get_path(self, path_name: str) -> str:
        """
        获取路径常量
        
        Args:
            path_name: 路径名称（如 'LOCAL_EQUIVALENT', 'REMOTE_ROOT' 等）
            
        Returns:
            str: 路径字符串
        """
        return self._default_paths.get(path_name, "")
    
    def get_folder_id(self, folder_name: str) -> Optional[str]:
        """
        获取文件夹ID常量
        
        Args:
            folder_name: 文件夹名称（如 'REMOTE_ROOT_FOLDER_ID' 等）
            
        Returns:
            Optional[str]: 文件夹ID
        """
        return self._default_folder_ids.get(folder_name)
    
    def set_path(self, path_name: str, path_value: str):
        """
        设置路径常量
        
        Args:
            path_name: 路径名称
            path_value: 路径值
        """
        self._default_paths[path_name] = path_value
    
    def set_folder_id(self, folder_name: str, folder_id: str):
        """
        设置文件夹ID常量
        
        Args:
            folder_name: 文件夹名称
            folder_id: 文件夹ID
        """
        self._default_folder_ids[folder_name] = folder_id
    
    def save_configuration(self):
        """保存当前配置到文件"""
        try:
            config = {}
            
            # 保存路径配置
            for key, value in self._default_paths.items():
                config[key.lower()] = value
            
            # 保存文件夹ID配置
            for key, value in self._default_folder_ids.items():
                if value is not None:
                    config[key.lower()] = value
            
            with open(self.SYNC_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Warning: Failed to save path configuration: {e}")
    
    def get_all_paths(self) -> Dict[str, str]:
        """获取所有路径常量"""
        return self._default_paths.copy()
    
    def get_all_folder_ids(self) -> Dict[str, Optional[str]]:
        """获取所有文件夹ID常量"""
        return self._default_folder_ids.copy()
    
    def update_dynamic_paths(self, mount_point: str):
        """
        更新动态挂载路径
        
        Args:
            mount_point: 挂载点路径
        """
        self.set_path("REMOTE_ROOT", f"{mount_point}/MyDrive/REMOTE_ROOT")
        self.set_path("REMOTE_ENV", f"{mount_point}/MyDrive/REMOTE_ENV")
    
    def detect_environment(self) -> str:
        """
        检测运行环境
        
        Returns:
            str: 环境类型 ('colab', 'macos', 'linux', 'windows')
        """
        import platform
        
        # 检测Colab环境
        try:
            import google.colab
            return "colab"
        except ImportError:
            pass
        
        # 检测操作系统
        system = platform.system()
        if system == "Darwin":
            return "macos"
        elif system == "Linux":
            return "linux"
        elif system == "Windows":
            return "windows"
        else:
            return "unknown"
    
    def setup_environment_defaults(self):
        """根据环境设置默认路径"""
        env = self.detect_environment()
        
        if env == "colab":
            # Colab环境设置
            self.set_path("REMOTE_ROOT", "/content/drive/MyDrive/REMOTE_ROOT")
            self.set_path("REMOTE_ENV", "/content/drive/MyDrive/REMOTE_ENV")
            self.set_path("DRIVE_EQUIVALENT", "/content/drive/MyDrive")
        elif env == "macos":
            # macOS环境设置
            self.set_path("REMOTE_ROOT", "/content/drive/MyDrive/REMOTE_ROOT")
            self.set_path("LOCAL_EQUIVALENT", str(self.HOME_DIR / "Applications/Google Drive"))
        
        # 保存配置
        self.save_configuration()


# 全局路径常量实例
path_constants = PathConstants()


# 便捷函数
def get_path(path_name: str) -> str:
    """获取路径常量的便捷函数"""
    return path_constants.get_path(path_name)


def get_folder_id(folder_name: str) -> Optional[str]:
    """获取文件夹ID的便捷函数"""
    return path_constants.get_folder_id(folder_name)


def get_data_dir() -> Path:
    """获取数据目录的便捷函数"""
    return path_constants.GOOGLE_DRIVE_DATA_DIR


def get_proj_dir() -> Path:
    """获取项目目录的便捷函数"""
    return path_constants.GOOGLE_DRIVE_PROJ_DIR


# 向后兼容的常量定义
LOCAL_EQUIVALENT = path_constants.get_path("LOCAL_EQUIVALENT")
DRIVE_EQUIVALENT = path_constants.get_path("DRIVE_EQUIVALENT")
REMOTE_ROOT = path_constants.get_path("REMOTE_ROOT")
REMOTE_ENV = path_constants.get_path("REMOTE_ENV")

HOME_FOLDER_ID = path_constants.get_folder_id("HOME_FOLDER_ID")
REMOTE_ROOT_FOLDER_ID = path_constants.get_folder_id("REMOTE_ROOT_FOLDER_ID")
REMOTE_ENV_FOLDER_ID = path_constants.get_folder_id("REMOTE_ENV_FOLDER_ID")
DRIVE_EQUIVALENT_FOLDER_ID = path_constants.get_folder_id("DRIVE_EQUIVALENT_FOLDER_ID")

HOME_URL = path_constants.HOME_URL


if __name__ == '__main__':
    # 测试路径常量管理器
    print("=== 路径常量管理器测试 ===")
    print(f"数据目录: {get_data_dir()}")
    print(f"项目目录: {get_proj_dir()}")
    print(f"REMOTE_ROOT: {get_path('REMOTE_ROOT')}")
    print(f"LOCAL_EQUIVALENT: {get_path('LOCAL_EQUIVALENT')}")
    print(f"环境类型: {path_constants.detect_environment()}")
    
    print("\n所有路径:")
    for name, path in path_constants.get_all_paths().items():
        print(f"  {name}: {path}")
    
    print("\n所有文件夹ID:")
    for name, folder_id in path_constants.get_all_folder_ids().items():
        print(f"  {name}: {folder_id}")
