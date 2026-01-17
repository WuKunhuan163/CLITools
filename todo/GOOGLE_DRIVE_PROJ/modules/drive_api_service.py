#!/usr/bin/env python3
"""
Google Drive Drive Api Service Module
"""

import sys
import subprocess
import warnings
import re
from pathlib import Path

def extract_folder_id_from_url(url):
    """从Google Drive文件夹URL中提取文件夹ID"""
    try:
        patterns = [
            r'/folders/([a-zA-Z0-9_-]+)',
            r'id=([a-zA-Z0-9_-]+)',
            r'folders/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
        
    except Exception as e:
        print(f"Extract folder ID failed: {e}")
        return None

def test_drive_folder_access(folder_id):
    """测试是否可以访问Google Drive文件夹"""
    try:
        drive_service = GoogleDriveService()
        result = drive_service.list_files(folder_id=folder_id, max_results=5)
        return result.get('success', False)
        
    except Exception as e:
        print(f"Test folder access failed: {e}")
        return False


def test_api_connection(command_identifier=None):
    """测试Google Drive API连接"""
    try:
        # 导入API服务
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "Error: API service file not found, please run GOOGLE_DRIVE --console-setup"
            print(error_msg)
            return 1
        
        # 运行API测试
        result = subprocess.run([
            sys.executable, str(api_service_path)
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            success_msg = "Google Drive API connection test successful"
            print(success_msg)
            print(result.stdout)
            return 0
        else:
            error_msg = f"Error: API connection test failed: {result.stderr}"
            print(error_msg)
            return 1
            
    except subprocess.TimeoutExpired:
        timeout_msg = "API test timeout"
        print(timeout_msg)
        return 1
    except Exception as e:
        error_msg = f"Error: Error testing API connection: {e}"
        print(error_msg)
        return 1

def list_drive_files(command_identifier=None, max_results=10):
    """列出Google Drive文件"""
    try:
        # 导入并使用API服务
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "Error: API service file not found, please run GOOGLE_DRIVE --console-setup"
            print(error_msg)
            return 1
        
        # 动态导入API服务
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        # 创建服务实例
        drive_service = GoogleDriveService()
        
        # 列出文件
        result = drive_service.list_files(max_results=max_results)
        
        if result['success']:
            print(f"Google Drive file list (first {max_results} files):")
            print(f"-" * 50)
            for file in result['files']:
                file_type = "📁" if file['mimeType'] == 'application/vnd.google-apps.folder' else "📄"
                print(f"{file_type} {file['name']}")
                print(f"ID: {file['id']}")
                print(f"Type: {file['mimeType']}")
                if 'size' in file:
                    print(f"Size: {file['size']} bytes")
                print()
            return 0
        else:
            error_msg = f"Error: Listing files failed: {result['error']}"
            print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"Error: Error listing Drive files: {e}"
        print(error_msg)
        return 1
