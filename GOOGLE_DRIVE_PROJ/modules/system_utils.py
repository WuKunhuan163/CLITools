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

def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False

def write_to_json_output(data, command_identifier=None):
    """将结果写入到指定的 JSON 输出文件中"""
    from pathlib import Path
    
    if not is_run_environment(command_identifier):
        return False
        
    if command_identifier:
        output_file = os.environ.get(f'RUN_DATA_FILE_{command_identifier}')
    else:
        output_file = os.environ.get('RUN_DATA_FILE')
    
    if not output_file:
        return False
    
    try:
        # 确保输出目录存在
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing to JSON output file: {e}")
        return False
