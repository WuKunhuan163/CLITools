"""
System utilities - 系统相关的工具函数
从file_operations.py迁移而来
"""
import os, json

def ensure_google_drive_desktop_running():
    """
    Ensure Google Drive Desktop is running
    Returns:
        bool: True if Google Drive Desktop is running or successfully started,
              False otherwise
    """
    try:
        import subprocess
        import platform
        import time
        
        # Check if running
        result = subprocess.run(['pgrep', '-f', 'Google Drive'], 
                              capture_output=True, text=True)
        if result.returncode == 0 and bool(result.stdout.strip()):
            return True
        
        if platform.system() == "Darwin":
            subprocess.run(['open', '-a', 'Google Drive'], check=False)
        elif platform.system() == "Linux":
            subprocess.run(['google-drive'], check=False)
        elif platform.system() == "Windows":
            subprocess.run(['start', 'GoogleDrive'], shell=True, check=False)
        
        # Wait for startup
        for i in range(10):
            time.sleep(1)
            result = subprocess.run(['pgrep', '-f', 'Google Drive'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and bool(result.stdout.strip()):
                print(f"Google Drive Desktop started successfully")
                return True
        
        print(f"Could not confirm Google Drive Desktop startup")
        return False
        
    except Exception as e:
        print(f"Error: Error managing Google Drive Desktop: {e}")
        return False
