#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器 - 统一管理所有常量和配置
提高系统维护性，避免硬编码
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


class ConfigLoader:
    """配置加载器单例类"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        current_dir = Path(__file__).parent.parent.parent
        config_file = current_dir / "GOOGLE_DRIVE_DATA" / "config.json"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            self._config = json.load(f)

    def get(self, key_path: str, default=None):
        """
        获取配置值，支持点号分隔的路径
        
        Args:
            key_path: 配置键路径，如 'constants.HOME_URL' 或 'queue_settings.timeout_hours'
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            keys = key_path.split('.')
            value = self._config
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            
            return value
            
        except Exception:
            return default


    def __getattr__(self, name):
        """允许通过属性访问配置值，例如 config.HOME_URL"""
        # 尝试从constants中获取
        value = self.get(f'constants.{name}')
        if value is not None:
            return value
        # 尝试从queue_settings中获取
        value = self.get(f'queue_settings.{name}')
        if value is not None:
            return value
        # 尝试从file_paths中获取
        value = self.get(f'file_paths.{name}')
        if value is not None:
            return value
        # 如果都没找到，抛出AttributeError
        raise AttributeError(f"'ConfigLoader' object has no attribute '{name}'")

# 全局配置实例
_config_loader = None

def get_config() -> ConfigLoader:
    """获取配置加载器单例"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader

# Background任务文件名模板
BG_STATUS_FILE_TEMPLATE = "cmd_bg_{bg_pid}.status"
BG_SCRIPT_FILE_TEMPLATE = "cmd_bg_{bg_pid}.sh"
BG_LOG_FILE_TEMPLATE = "cmd_bg_{bg_pid}.log"
BG_RESULT_FILE_TEMPLATE = "cmd_bg_{bg_pid}.result.json"

# 生成具体文件名的辅助函数
def get_bg_status_file(bg_pid):
    """获取background状态文件名"""
    return BG_STATUS_FILE_TEMPLATE.format(bg_pid=bg_pid)

def get_bg_script_file(bg_pid):
    """获取background脚本文件名"""
    return BG_SCRIPT_FILE_TEMPLATE.format(bg_pid=bg_pid)

def get_bg_log_file(bg_pid):
    """获取background日志文件名"""
    return BG_LOG_FILE_TEMPLATE.format(bg_pid=bg_pid)

def get_bg_result_file(bg_pid):
    """获取background结果文件名"""
    return BG_RESULT_FILE_TEMPLATE.format(bg_pid=bg_pid)
