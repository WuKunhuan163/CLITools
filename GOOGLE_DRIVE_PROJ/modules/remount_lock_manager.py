#!/usr/bin/env python3
"""
Remount Lock Manager - 管理remount过程的锁机制
防止多个remount窗口同时弹出
"""

import time
import json
import os
import threading
from pathlib import Path


class RemountLockManager:
    """Remount锁管理器"""
    
    def __init__(self):
        self._local_lock = threading.Lock()  # 进程内锁
        
    def _get_lock_file_path(self):
        """获取锁文件路径"""
        try:
            from .path_constants import PathConstants
            path_constants = PathConstants()
            return path_constants.GOOGLE_DRIVE_DATA_DIR / "remount_in_progress.lock"
        except ImportError:
            # Fallback for standalone usage
            from pathlib import Path
            return Path.home() / ".local/bin/GOOGLE_DRIVE_DATA/remount_in_progress.lock"
    
    def _get_flag_file_path(self):
        """获取remount flag文件路径"""
        try:
            from .path_constants import PathConstants
            path_constants = PathConstants()
            return path_constants.GOOGLE_DRIVE_DATA_DIR / "remount_required.flag"
        except ImportError:
            # Fallback for standalone usage
            from pathlib import Path
            return Path.home() / ".local/bin/GOOGLE_DRIVE_DATA/remount_required.flag"
    
    def acquire_remount_lock(self, caller_info="Unknown", force=False):
        """
        尝试获取remount锁
        
        Args:
            caller_info: 调用者信息，用于调试
            force: 是否强制获取锁（不检查flag文件）。用于手动remount命令。
            
        Returns:
            bool: True表示成功获取锁，False表示锁已被占用或无需remount
        """
        with self._local_lock:
            try:
                lock_file = self._get_lock_file_path()
                flag_file = self._get_flag_file_path()
                
                # 首先检查是否有remount flag（除非force=True）
                if not force and not flag_file.exists():
                    # 没有flag，无需remount
                    return False
                
                # 尝试原子性创建锁文件（参考window_manager的实现）
                if not lock_file.exists():
                    try:
                        # 使用'x'模式确保原子性创建
                        lock_data = {
                            "pid": os.getpid(),
                            "caller": caller_info,
                            "acquired_at": time.time(),
                            "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        with open(lock_file, 'x') as f:  # 'x' 模式确保原子性创建
                            json.dump(lock_data, f, indent=2)
                            f.flush()
                            os.fsync(f.fileno())  # 强制写入磁盘
                        
                        # 再次验证锁文件内容（防止竞态条件）
                        time.sleep(0.01)  # 短暂等待
                        with open(lock_file, 'r') as f:
                            stored_data = json.load(f)
                        
                        if stored_data.get('pid') == os.getpid():
                            # 成功获取锁
                            return True
                        else:
                            # 其他进程获取了锁
                            return False
                            
                    except FileExistsError:
                        # 文件已存在，其他进程获取了锁
                        pass
                    except Exception:
                        # 创建失败
                        return False
                
                # 锁文件已存在，检查是否过期或进程是否存活
                try:
                    with open(lock_file, 'r') as f:
                        lock_data = json.load(f)
                    
                    lock_pid = lock_data.get('pid')
                    lock_time = lock_data.get('acquired_at', 0)
                    
                    # 检查进程是否还存活
                    try:
                        import psutil
                        if lock_pid and psutil.pid_exists(lock_pid):
                            # 进程存活，检查时间是否过期
                            if time.time() - lock_time < 300:  # 5分钟内
                                return False  # 锁仍然有效
                    except ImportError:
                        # 没有psutil，只检查时间
                        if time.time() - lock_time < 300:  # 5分钟内
                            return False
                    
                    # 锁已过期或进程不存在，清理并重试
                    lock_file.unlink()
                    # 递归重试一次
                    return self.acquire_remount_lock(caller_info)
                    
                except Exception:
                    # 无法读取锁文件，尝试删除
                    try:
                        lock_file.unlink()
                        return self.acquire_remount_lock(caller_info)
                    except Exception:
                        return False
                
            except Exception as e:
                # 获取锁失败
                return False
    
    def release_remount_lock(self, caller_info="Unknown"):
        """
        释放remount锁
        
        Args:
            caller_info: 调用者信息，用于调试
        """
        with self._local_lock:
            try:
                lock_file = self._get_lock_file_path()
                
                if lock_file.exists():
                    # 验证锁是否属于当前进程
                    try:
                        with open(lock_file, 'r') as f:
                            lock_data = json.load(f)
                        
                        if lock_data.get('pid') == os.getpid():
                            # 锁属于当前进程，可以释放
                            lock_file.unlink()
                        # 如果不属于当前进程，不做任何操作
                    except Exception:
                        # 如果无法读取锁文件，尝试强制删除
                        try:
                            lock_file.unlink()
                        except Exception:
                            pass
                            
            except Exception as e:
                # 释放锁失败，静默处理
                pass
    
    def is_remount_in_progress(self):
        """
        检查是否有remount正在进行
        
        Returns:
            bool: True表示有remount正在进行
        """
        try:
            lock_file = self._get_lock_file_path()
            
            if not lock_file.exists():
                return False
            
            # 检查锁文件是否过期
            try:
                lock_stat = lock_file.stat()
                if time.time() - lock_stat.st_mtime > 300:  # 5分钟
                    # 清理过期锁文件
                    lock_file.unlink()
                    return False
                else:
                    return True
            except Exception:
                return False
                
        except Exception:
            return False
    
    def wait_for_remount_completion(self, max_wait_seconds=None):
        """
        等待remount完成
        
        Args:
            max_wait_seconds: 最大等待时间（秒），None表示无超时限制
            
        Returns:
            bool: True表示remount已完成，False表示超时（仅当max_wait_seconds不为None时）
        """
        start_time = time.time()
        
        while True:
            # 如果设置了超时，检查是否超时
            if max_wait_seconds is not None and (time.time() - start_time) >= max_wait_seconds:
                return False  # 超时
            
            # 检查flag是否还存在
            flag_file = self._get_flag_file_path()
            if not flag_file.exists():
                # flag已被清除，remount完成
                return True
            
            # 检查是否有remount正在进行
            if not self.is_remount_in_progress():
                # 没有remount在进行，但flag仍存在
                # 可能需要触发新的remount
                break
            
            time.sleep(0.5)  # 每0.5秒检查一次
        
        return False  # flag存在但没有remount在进行


# 全局锁管理器实例
_remount_lock_manager = None

def get_remount_lock_manager():
    """获取全局remount锁管理器实例"""
    global _remount_lock_manager
    if _remount_lock_manager is None:
        _remount_lock_manager = RemountLockManager()
    return _remount_lock_manager
