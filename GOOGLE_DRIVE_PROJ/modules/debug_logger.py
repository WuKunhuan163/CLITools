#!/usr/bin/env python3
"""
Debug日志系统 - 将整个流程的debug信息写入GOOGLE_DRIVE_DATA中的日志json
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import threading

class DebugLogger:
    """Debug日志管理器"""
    
    def __init__(self):
        self.log_entries = []
        self.session_id = f"session_{int(time.time())}_{os.getpid()}"
        self.lock = threading.Lock()
        
        # 确定日志文件路径
        self.log_dir = self._get_log_directory()
        self.log_file = self.log_dir / f"gds_debug_{self.session_id}.json"
        
        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化日志文件
        self._write_log_file()
    
    def _get_log_directory(self):
        """获取日志目录路径"""
        # 使用当前项目的GOOGLE_DRIVE_DATA目录
        # 当前文件: GOOGLE_DRIVE_PROJ/modules/debug_logger.py
        # 项目根: GOOGLE_DRIVE_PROJ/..
        # 目标目录: GOOGLE_DRIVE_PROJ/../GOOGLE_DRIVE_DATA/debug_logs
        current_file = Path(__file__).resolve()  # .../GOOGLE_DRIVE_PROJ/modules/debug_logger.py
        project_root = current_file.parent.parent.parent  # .../
        base_dir = project_root / 'GOOGLE_DRIVE_DATA'
        
        return base_dir / 'debug_logs'
    
    def log(self, component, event, data=None, level='INFO'):
        """记录debug信息
        
        Args:
            component (str): 组件名称 (如 'command_generator', 'path_resolver')
            event (str): 事件名称 (如 'expand_paths_with_bash', 'generate_command')
            data (dict): 相关数据
            level (str): 日志级别 ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        """
        # 添加debug print确认函数被调用
        # print(f"[DEBUG_LOGGER] {component}.{event} - {level}")
        # 输出日志文件名（便于追踪） - 禁用，输出太多
        # print(f"[DEBUG_LOG] {self.log_file}", file=sys.stderr, flush=True)
        
        with self.lock:
            entry = {
                'timestamp': datetime.now().isoformat(),
                'session_id': self.session_id,
                'component': component,
                'event': event,
                'level': level,
                'data': data or {}
            }
            
            self.log_entries.append(entry)
            
            # 立即写入每个条目（确保不会丢失）
            self._write_log_file()
    
    def _write_log_file(self):
        """将日志条目写入文件"""
        log_data = {
            'session_info': {
                'session_id': self.session_id,
                'start_time': datetime.now().isoformat(),
                'pid': os.getpid(),
                'cwd': os.getcwd()
            },
            'entries': self.log_entries
        }
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
    def flush(self):
        """强制写入所有日志条目"""
        with self.lock:
            self._write_log_file()
    
    def get_log_file_path(self):
        """获取当前日志文件路径"""
        return str(self.log_file)

# 全局debug logger实例
_debug_logger = None

def get_debug_logger():
    """获取全局debug logger实例"""
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = DebugLogger()
    return _debug_logger

def debug_log(component, event, data=None, level='DEBUG'):
    """便捷的debug日志函数"""
    logger = get_debug_logger()
    logger.log(component, event, data, level)

def info_log(component, event, data=None):
    """便捷的info日志函数"""
    debug_log(component, event, data, 'INFO')

def error_log(component, event, data=None):
    """便捷的error日志函数"""
    debug_log(component, event, data, 'ERROR')

def flush_debug_logs():
    """刷新所有debug日志"""
    global _debug_logger
    if _debug_logger:
        _debug_logger.flush()

def get_debug_log_path():
    """获取当前debug日志文件路径"""
    logger = get_debug_logger()
    return logger.get_log_file_path()

if __name__ == "__main__":
    # 测试debug logger
    debug_log('test_component', 'test_event', {'test_data': 'hello world'})
    info_log('test_component', 'info_event', {'info': 'test info'})
    error_log('test_component', 'error_event', {'error': 'test error'})
    
    logger = get_debug_logger()
    print(f"Debug log file: {logger.get_log_file_path()}")
    logger.flush()
