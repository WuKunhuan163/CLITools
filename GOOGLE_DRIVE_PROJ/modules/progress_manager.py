#!/usr/bin/env python3
"""
Google Drive Shell - Progress Manager Module

This module provides comprehensive progress display and management functionality for the
Google Drive Shell system. It handles visual feedback for long-running operations using
ANSI escape sequences and thread-safe progress tracking.

Key Features:
- Real-time progress display with ANSI escape sequences
- Thread-safe progress tracking for concurrent operations
- Buffered progress messages to prevent output conflicts
- Automatic progress cleanup and restoration
- Integration with remote command execution
- Support for various progress indicators (spinners, percentages, messages)

Progress Types:
- Spinner progress: Animated indicators for indeterminate operations
- Message progress: Text-based status updates
- Buffered progress: Queued messages for sequential display
- Validation progress: File existence and operation verification

Classes:
    ProgressDisplay: Main progress display manager with ANSI support
    ProgressManager: High-level progress coordination and management

Display Features:
- ANSI escape sequence support for terminal control
- Progress message buffering and queuing
- Automatic cleanup on completion or interruption
- Thread-safe operations for concurrent progress updates

Dependencies:
    - Threading support for concurrent progress tracking
    - ANSI terminal support for visual indicators
    - System utilities for terminal control
    - Integration with command execution pipeline

Based on: test_progress_display.py successful implementation
"""

import sys
import threading
import time
from typing import Optional, List


class ProgressDisplay:
    """进度显示管理器，使用ANSI转义序列实现进度显示"""
    
    def __init__(self):
        self.is_active = False
        self.lock = threading.Lock()
        self.current_message = ""
        self.has_progress_line = False

    def start_progress(self, message: str = "⏳ Waiting for result ..."):
        """开始显示进度"""
        with self.lock:
            if not self.is_active:
                self.is_active = True
                self.current_message = message
                self.has_progress_line = True
                
                # 确保清除当前行并从行首开始输出进度信息
                print(f'\r\033[K{message}', end='', flush=True)
    
    def update_progress(self, addition: str = "."):
        """更新进度信息（添加内容）"""
        with self.lock:
            if self.is_active and self.has_progress_line:
                # 添加进度指示符（如点）
                print(addition, end='', flush=True)
    
    def stop_progress(self):
        """停止进度显示并清除"""
        with self.lock:
            # 强制清除当前行，无论状态如何
            print('\r\033[K', end='', flush=True)
            self.is_active = False
            self.has_progress_line = False
            self.current_message = ""

# 全局进度显示实例
_global_progress_display = ProgressDisplay()

# 导出的函数接口
def start_progress_buffering(message: str = "⏳ Waiting for result ..."):
    """开始进度显示"""
    _global_progress_display.start_progress(message)

def stop_progress_buffering():
    """停止进度显示"""
    _global_progress_display.stop_progress()

def is_progress_active():
    """检查进度显示是否激活"""
    return _global_progress_display.is_active

def progress_print(message: str, end: str = "\n", flush: bool = False):
    """更新进度信息（添加点或其他内容）"""
    if end == "" or end == "\n":
        # 如果是添加点的情况
        addition = message.strip()
        if addition in [".", "⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]:
            _global_progress_display.update_progress(addition)
        else:
            # 如果是更新整个进度信息，先清除再重新开始
            _global_progress_display.stop_progress()
            _global_progress_display.start_progress(message)
    else:
        _global_progress_display.update_progress(message)

def clear_progress():
    """清除进度显示"""
    _global_progress_display.stop_progress()

def add_success_mark():
    """添加成功标记到进度显示"""
    _global_progress_display.update_progress(" ✓")

def interruptible_progress_loop(progress_message, loop_func, check_interval=1.0, max_attempts=None):
    """
    统一的可中断进度循环接口
    
    Args:
        progress_message (str): 进度显示消息
        loop_func (callable): 循环检查函数，返回True表示完成，False表示继续，None表示失败
        check_interval (float): 检查间隔（秒）
        max_attempts (int): 最大尝试次数，None表示无限制
        
    Returns:
        dict: {"success": bool, "cancelled": bool, "message": str, "attempts": int}
    """
    import time
    import signal
    import sys
    
    # 开始进度显示
    if _global_progress_display.is_active:
        clear_progress()
    start_progress_buffering(progress_message)
    
    # 设置中断标志
    interrupted = False
    
    def signal_handler(signum, frame):
        nonlocal interrupted
        interrupted = True
    
    # 保存原有的信号处理器
    old_handler = signal.signal(signal.SIGINT, signal_handler)
    
    try:
        attempt = 0
        while max_attempts is None or attempt < max_attempts:
            attempt += 1
            
            # 检查中断标志
            if interrupted:
                raise KeyboardInterrupt()
            
            # 执行检查函数前再次检查中断（防止在loop_func执行前被中断）
            if interrupted:
                raise KeyboardInterrupt()
            
            # 执行检查函数
            try:
                result = loop_func()
                
                # 检查函数执行后立即检查中断（防止在loop_func期间被中断）
                if interrupted:
                    raise KeyboardInterrupt()
                
                if result is True:
                    # 成功完成
                    clear_progress()
                    return {
                        "success": True,
                        "cancelled": False,
                        "message": "Operation completed successfully",
                        "attempts": attempt
                    }
                elif result is None:
                    # 失败，退出循环
                    break
                # result is False: 继续循环
            except KeyboardInterrupt:
                # 立即传播KeyboardInterrupt
                raise
            except Exception as e:
                # 循环函数异常，继续重试
                pass
            
            # 等待下一次检查，支持中断
            if check_interval > 0:
                sleep_time = 0
                while sleep_time < check_interval:
                    if interrupted:
                        raise KeyboardInterrupt()
                    time.sleep(0.1)
                    sleep_time += 0.1
                    
                # 显示进度点
                progress_print(".")
                
    except KeyboardInterrupt:
        # 用户中断
        clear_progress()
        return {
            "success": False,
            "cancelled": True,
            "message": "Operation cancelled by user",
            "attempts": attempt
        }
    finally:
        # 恢复原有的信号处理器
        try:
            signal.signal(signal.SIGINT, old_handler)
        except:
            pass
    
    # 超时或失败
    clear_progress()
    return {
        "success": False,
        "cancelled": False,
        "message": f"Operation failed after {attempt} attempts",
        "attempts": attempt
    }

def validate_creation(validation_func, item_name, max_attempts=12, validation_type="file"):
    """
    统一的文件/目录验证接口，集成进度显示
    使用统一的可中断进度循环接口
    
    Args:
        validation_func: 验证函数，返回True表示成功，False表示需要重试
        item_name: 验证的项目名称（文件名或目录名）
        max_attempts: 最大重试次数
        validation_type: 验证类型 ("file", "dir", "upload")
        
    Returns:
        dict: {"success": bool, "message": str, "attempts": int, "cancelled": bool}
    """
    # 确定进度消息
    if validation_type == "file":
        progress_message = f"⏳ Validating file existence ..."
        success_msg = f"File {item_name} created successfully"
    elif validation_type == "dir":
        progress_message = f"⏳ Validating directory existence ..."
        success_msg = f"Directory {item_name} created successfully"
    elif validation_type == "upload":
        progress_message = f"⏳ Validating {item_name} upload progress ..."
        success_msg = f"{item_name} uploaded successfully"
    else:
        progress_message = f"⏳ Validating {validation_type} ..."
        success_msg = f"{item_name} {validation_type} completed"
    
    # 使用统一的可中断进度循环
    result = interruptible_progress_loop(
        progress_message=progress_message,
        loop_func=validation_func,
        check_interval=1.0,
        max_attempts=max_attempts
    )
    
    # 转换结果格式
    if result["success"]:
        result["message"] = success_msg
    elif result["cancelled"]:
        result["message"] = f"Validation of {item_name} cancelled by user"
    else:
        result["message"] = f"Validation of {item_name} failed after {result['attempts']} attempts"
    
    return result