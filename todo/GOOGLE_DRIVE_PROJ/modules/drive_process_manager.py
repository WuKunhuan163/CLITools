#!/usr/bin/env python3
"""
Google Drive - Drive Process Manager Module
"""

import subprocess
import time
import warnings

# 全局常量
def is_google_drive_running():
    """检查Google Drive Desktop是否正在运行"""
    try:
        result = subprocess.run(['pgrep', '-f', 'Google Drive'], 
                              capture_output=True, text=True)
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False

def get_google_drive_processes():
    """获取Google Drive进程信息"""
    try:
        result = subprocess.run(['pgrep', '-f', 'Google Drive'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            return [pid for pid in pids if pid]
        return []
    except Exception:
        return []

def shutdown_google_drive(command_identifier=None):
    """关闭Google Drive Desktop"""
    try:
        if not is_google_drive_running():
            print("Google Drive is already stopped")
            return 0
        
        # 尝试优雅关闭
        subprocess.run(['killall', 'Google Drive'], 
                     capture_output=True, text=True)
        
        # 等待一下让进程完全关闭
        time.sleep(2)
        
        # 检查是否成功关闭
        if not is_google_drive_running():
            print("Google Drive has been closed")
            return 0
        else:
            pids = get_google_drive_processes()
            for pid in pids:
                subprocess.run(['kill', '-9', pid], capture_output=True)
            
            time.sleep(1)
            
            if not is_google_drive_running():
                print("Google Drive has been closed")
                return 0
            else:
                print("Cannot close Google Drive")
                return 1
                
    except Exception as e:
        print(f"关闭 Google Drive 时出错: {e}")
        return 1

def launch_google_drive(command_identifier=None):
    """启动Google Drive Desktop"""
    try:
        if is_google_drive_running():
            print("Google Drive 已经在运行")
            return 0
        
        print(f"Launching Google Drive...")
        
        # 启动Google Drive
        result = subprocess.run(['open', '-a', 'Google Drive'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Failed to launch Google Drive: {result.stderr}")
            return 1
        
        # 等待启动
        max_wait = 10  # 最多等待10秒
        for i in range(max_wait):
            time.sleep(1)
            if is_google_drive_running():
                print(f"Google Drive has been launched (startup time {i+1} seconds)")
                return 0
        
        # 超时但可能已启动
        if is_google_drive_running():
            print("Google Drive has been launched (startup time longer)")
            return 0
        else:
            print("Google Drive startup timeout")
            return 1
            
    except Exception as e:
        print(f"启动 Google Drive 时出错: {e}")
        return 1

def restart_google_drive(command_identifier=None):
    """重启Google Drive Desktop"""
    try:
        print(f"Restarting Google Drive...")
        
        # 先关闭
        shutdown_result = shutdown_google_drive(command_identifier)
        if shutdown_result != 0:
            print("Restart failed - shutdown phase failed")
            return 1
        
        # 等待一下确保完全关闭
        time.sleep(3)
        
        # 再启动
        launch_result = launch_google_drive(command_identifier)
        if launch_result != 0:
            print("Restart failed - launch phase failed")
            return 1
        
        print("Google Drive has been restarted")
        return 0
        
    except Exception as e:
        print(f"Restart Google Drive failed: {e}")
        return 1
